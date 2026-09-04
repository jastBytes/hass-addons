#!/usr/bin/env python
# (c) 2021 Andreas Böhler
# License: Apache 2.0


import paho.mqtt.client as mqtt
import select
import socket
import json
import yaml
import os
import sys
import threading
import time
import requests

DEFAULT_MEDIOLA_ID = 'mediola'
DEFAULT_LISTEN_PORTS = [1902, 1901]
REQUEST_TIMEOUT = 5
TICK_INTERVAL = 0.2
POSITION_PUBLISH_INTERVAL = 0.5
STATE_FILE_NAME = 'mediola2mqtt_state.json'

# Somfy RTS (RT) command prefixes, the address is appended
RT_COMMANDS = {
    'open': '20',
    'close': '40',
    'stop': '10',
}

# Elero (ER) command suffixes, appended to the hexadecimal channel
ER_COMMANDS = {
    'open': '01',
    'close': '00',
    'stop': '02',
    'intermediate': '04',
    'ventilation': '08',
}

# Elero status codes as reported by the gateway
ER_STATE_OPEN = ('01', '0e')
ER_STATE_CLOSED = ('02', '0f')
ER_STATE_OPENING = ('08', '0a')
ER_STATE_CLOSING = ('09', '0b')
# 03: intermediate position, 04: ventilation position, 05: blocking,
# 0d: stopped in an undefined position
ER_STATE_STOPPED = ('03', '04', '05', '0d')


def load_config():
    if os.path.exists('/data/options.json'):
        print('Running in hass.io add-on mode')
        with open('/data/options.json', 'r') as fp:
            return json.load(fp), '/data'
    elif os.path.exists('/config/mediola2mqtt.yaml'):
        print('Running in legacy add-on mode')
        with open('/config/mediola2mqtt.yaml', 'r') as fp:
            return yaml.safe_load(fp), '/config'
    elif os.path.exists('mediola2mqtt.yaml'):
        print('Running in local mode')
        with open('mediola2mqtt.yaml', 'r') as fp:
            return yaml.safe_load(fp), '.'
    else:
        print('Configuration file not found, exiting.')
        sys.exit(1)


config, state_dir = load_config()

general = config.get('general') or {}
debug = bool(config['mqtt'].get('debug'))
availability_topic = config['mqtt']['topic'] + '/status'
state_file = os.path.join(state_dir, STATE_FILE_NAME)

lock = threading.RLock()
command_handlers = {}
resolved_hosts = {}
poll_thread = None


def log(message):
    print(message, flush=True)


def debug_log(message):
    if debug:
        log(message)


class Blind:
    """A single cover, including its simulated position."""

    def __init__(self, cfg):
        self.type = cfg['type']
        self.adr = str(cfg['adr'])
        self.name = cfg.get('name', 'Mediola Blind')
        self.mediolaid = cfg.get('mediola', DEFAULT_MEDIOLA_ID)
        self.device_class = cfg.get('device_class', 'blind')
        self.intermediate_position = bool(cfg.get('intermediate_position', False))
        self.ventilation_position = bool(cfg.get('ventilation_position', False))

        # Travel times enable position reporting. If only one of them is
        # configured, it is used for both directions.
        travel_up = cfg.get('travel_time_up')
        travel_down = cfg.get('travel_time_down')
        if travel_up is None:
            travel_up = travel_down
        if travel_down is None:
            travel_down = travel_up
        self.travel_up = float(travel_up) if travel_up else 0.0
        self.travel_down = float(travel_down) if travel_down else 0.0
        self.tracks_position = self.travel_up > 0 and self.travel_down > 0

        # 100 = fully open, 0 = closed, None = unknown
        self.position = None
        self.direction = 0
        self.target = None
        self.pending_target = None
        self.last_tick = None
        self.published_position = None
        self.published_state = None
        self.last_position_publish = 0.0

    @property
    def identifier(self):
        return self.type + '_' + self.adr

    @property
    def unique_id(self):
        return self.mediolaid + '_' + self.identifier

    def matches(self, dtype, address):
        """Compare against an address as reported by the gateway."""
        if self.type != dtype:
            return False
        if dtype == 'ER':
            try:
                return int(self.adr) == int(address, 16)
            except (TypeError, ValueError):
                return False
        return self.adr.lower() == str(address).lower()

    def begin_move(self, direction, target):
        if not self.tracks_position:
            self.direction = 0
            return
        if self.position is None:
            # The position is unknown, assume the worst case so that a full
            # open/close drive takes the complete travel time.
            self.position = 0.0 if direction > 0 else 100.0
        self.direction = direction
        self.target = target
        self.pending_target = None
        self.last_tick = time.monotonic()

    def halt(self):
        self.direction = 0
        self.target = None
        self.pending_target = None
        self.last_tick = None

    def set_position(self, position):
        if self.tracks_position:
            self.position = position

    def advance(self, now):
        """Advance the simulated position, returns True if the target is hit."""
        travel = self.travel_up if self.direction > 0 else self.travel_down
        elapsed = now - (self.last_tick if self.last_tick else now)
        self.last_tick = now
        if travel <= 0:
            return True
        self.position += self.direction * elapsed * 100.0 / travel
        if self.direction > 0 and self.position >= self.target:
            self.position = min(self.target, 100.0)
            return True
        if self.direction < 0 and self.position <= self.target:
            self.position = max(self.target, 0.0)
            return True
        self.position = max(0.0, min(100.0, self.position))
        return False

    def state_payload(self):
        if self.direction > 0:
            return 'opening'
        if self.direction < 0:
            return 'closing'
        if self.position is None:
            return None
        return 'closed' if self.position <= 0.5 else 'open'


blinds = [Blind(cfg) for cfg in config.get('blinds') or []]
buttons = config.get('buttons') or []


def iter_mediolas():
    if isinstance(config['mediola'], list):
        return config['mediola']
    return [config['mediola']]


def get_mediola(mediolaid):
    if not isinstance(config['mediola'], list):
        return config['mediola']
    for mediola in config['mediola']:
        if mediola.get('id') == mediolaid:
            return mediola
    return None


def get_mediola_id(mediola):
    return mediola.get('id', DEFAULT_MEDIOLA_ID)


def send_request(mediolaid, params):
    """Send a request to a gateway, returns the response body or None."""
    mediola = get_mediola(mediolaid)
    if not mediola or not mediola.get('host'):
        log('Error: Could not find matching Mediola!')
        return None
    payload = dict(params)
    if mediola.get('password'):
        payload['XC_PASS'] = mediola['password']
    url = 'http://' + mediola['host'] + mediola.get('path', '/command')
    try:
        response = requests.get(url, params=payload,
                                headers={'Connection': 'close'},
                                timeout=REQUEST_TIMEOUT)
    except requests.RequestException as exc:
        log('Error talking to Mediola %s: %s' % (mediola['host'], exc))
        return None
    if response.status_code != 200:
        log('Mediola %s returned HTTP %d' % (mediola['host'], response.status_code))
        return None
    return response.text


def parse_response(text):
    """Parse a gateway response, returns the payload or None on error."""
    if text is None:
        return None
    text = text.strip()
    if text.startswith('{XC_ERR}'):
        log('Mediola returned an error: %s' % text[len('{XC_ERR}'):])
        return None
    if text.startswith('{XC_SUC}'):
        text = text[len('{XC_SUC}'):].strip()
        if not text:
            return []
    try:
        parsed = json.loads(text)
    except ValueError:
        return None
    if isinstance(parsed, dict):
        if 'XC_SUC' in parsed:
            return parsed['XC_SUC']
        if 'XC_ERR' in parsed:
            log('Mediola returned an error: %s' % parsed['XC_ERR'])
            return None
    return parsed


def send_blind_command(blind, action):
    if blind.type == 'RT':
        if action not in RT_COMMANDS:
            log('Command %s is not supported for Somfy blinds' % action)
            return False
        data = RT_COMMANDS[action] + blind.adr
    elif blind.type == 'ER':
        if action not in ER_COMMANDS:
            log('Command %s is not supported for Elero blinds' % action)
            return False
        try:
            channel = format(int(blind.adr), '02x')
        except ValueError:
            log('Invalid Elero address %s, expecting a decimal number' % blind.adr)
            return False
        data = channel + ER_COMMANDS[action]
    else:
        log('Unknown blind type %s' % blind.type)
        return False

    payload = {
        'XC_FNC': 'SendSC',
        'type': blind.type,
        'data': data,
    }
    return send_request(blind.mediolaid, payload) is not None


def blind_topic(blind):
    return config['mqtt']['topic'] + '/blinds/' + blind.mediolaid + '/' + blind.identifier


def load_positions():
    if not os.path.exists(state_file):
        return
    try:
        with open(state_file, 'r') as fp:
            stored = json.load(fp)
    except (OSError, ValueError) as exc:
        log('Could not read stored positions: %s' % exc)
        return
    for blind in blinds:
        position = stored.get(blind.unique_id)
        if blind.tracks_position and isinstance(position, (int, float)):
            blind.position = max(0.0, min(100.0, float(position)))


def save_positions():
    stored = {}
    with lock:
        for blind in blinds:
            if blind.tracks_position and blind.position is not None:
                stored[blind.unique_id] = round(blind.position, 1)
    if not stored:
        return
    try:
        with open(state_file, 'w') as fp:
            json.dump(stored, fp)
    except OSError as exc:
        debug_log('Could not store positions: %s' % exc)


def publish_blind(blind, event_state=None, force=False):
    """Publish position and state, honouring the publish throttle."""
    now = time.monotonic()
    topic = blind_topic(blind)
    if blind.tracks_position and blind.position is not None:
        position = int(round(blind.position))
        if position != blind.published_position and \
           (force or now - blind.last_position_publish >= POSITION_PUBLISH_INTERVAL):
            blind.published_position = position
            blind.last_position_publish = now
            mqttc.publish(topic + '/position', payload=str(position), retain=True)
    state = blind.state_payload() if blind.tracks_position else None
    if state is None:
        state = event_state
    if state and state != blind.published_state:
        blind.published_state = state
        mqttc.publish(topic + '/state', payload=state, retain=True)


def handle_cover_command(blind, payload):
    command = payload.strip().lower()
    if command not in ('open', 'close', 'stop'):
        log('Wrong command: %s' % payload)
        return
    if not send_blind_command(blind, command):
        return
    with lock:
        if command == 'open':
            blind.begin_move(1, 100.0)
        elif command == 'close':
            blind.begin_move(-1, 0.0)
        else:
            blind.halt()
        publish_blind(blind, force=True)
    if command == 'stop':
        save_positions()


def handle_position_command(blind, payload):
    if not blind.tracks_position:
        log('Position control requires travel_time_up/travel_time_down for %s' % blind.name)
        return
    try:
        target = float(payload)
    except (TypeError, ValueError):
        log('Invalid position: %s' % payload)
        return
    target = max(0.0, min(100.0, target))

    with lock:
        current = blind.position

    pending = None
    if target >= 99.5:
        action, direction, stop_at = 'open', 1, 100.0
    elif target <= 0.5:
        action, direction, stop_at = 'close', -1, 0.0
    elif current is None:
        # Reference drive: close completely, then move to the requested
        # position once the bottom end stop is known to be reached.
        log('Position of %s is unknown, closing first to calibrate' % blind.name)
        action, direction, stop_at, pending = 'close', -1, 0.0, target
    elif target > current:
        action, direction, stop_at = 'open', 1, target
    elif target < current:
        action, direction, stop_at = 'close', -1, target
    else:
        return

    if not send_blind_command(blind, action):
        return
    with lock:
        blind.begin_move(direction, stop_at)
        blind.pending_target = pending
        publish_blind(blind, force=True)


def handle_preset_command(blind, action):
    if not send_blind_command(blind, action):
        return
    with lock:
        # The gateway does not tell us where the preset position actually is,
        # so the tracked position is invalidated. It is re-established by the
        # next full open/close drive or by a reference drive.
        blind.halt()
        blind.position = None
        blind.published_position = None
        publish_blind(blind, event_state='open', force=True)


def position_worker():
    while True:
        time.sleep(TICK_INTERVAL)
        now = time.monotonic()
        stops = []
        followups = []
        changed = False
        with lock:
            for blind in blinds:
                if not blind.tracks_position or blind.direction == 0:
                    continue
                if blind.advance(now):
                    at_end_stop = blind.target <= 0.0 or blind.target >= 100.0
                    pending = blind.pending_target
                    blind.halt()
                    if not at_end_stop:
                        # Intermediate positions have to be stopped explicitly,
                        # the end stops are handled by the motor itself.
                        stops.append(blind)
                    if pending is not None:
                        followups.append((blind, pending))
                    changed = True
                publish_blind(blind, force=blind.direction == 0)
        for blind in stops:
            send_blind_command(blind, 'stop')
        if changed:
            save_positions()
        for blind, pending in followups:
            handle_position_command(blind, pending)


# Define MQTT event callbacks
def on_connect(client, userdata, flags, rc):
    connect_statuses = {
        0: "Connected",
        1: "incorrect protocol version",
        2: "invalid client ID",
        3: "server unavailable",
        4: "bad username or password",
        5: "not authorised"
    }
    if rc != 0:
        print("MQTT: " + connect_statuses.get(rc, "Unknown error"))
    else:
        mqttc.publish(availability_topic, payload='online', retain=True)
        setup_discovery()
        start_polling()

def on_disconnect(client, userdata, rc):
    if rc != 0:
        print("Unexpected disconnection")
    else:
        print("Disconnected")

def on_message(client, obj, msg):
    print("Msg: " + msg.topic + " " + str(msg.qos) + " " + str(msg.payload))
    handler = command_handlers.get(msg.topic)
    if handler is None:
        debug_log('No handler for topic %s' % msg.topic)
        return
    try:
        payload = msg.payload.decode('utf-8')
    except UnicodeDecodeError:
        log('Received undecodable payload on %s' % msg.topic)
        return
    handler(payload)

def on_publish(client, obj, mid):
    print("Pub: " + str(mid))

def on_subscribe(client, obj, mid, granted_qos):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

def on_log(client, obj, level, string):
    print(string)


def device_payload(deviceid, name):
    return {
        "identifiers": deviceid,
        "manufacturer": "Mediola",
        "name": name,
    }


def availability_payload():
    return {
        "availability_topic": availability_topic,
        "payload_available": "online",
        "payload_not_available": "offline",
    }


def publish_discovery(component, object_id, payload):
    dtopic = config['mqtt']['discovery_prefix'] + '/' + component + '/' + object_id + '/config'
    mqttc.publish(dtopic, payload=json.dumps(payload), retain=True)


def subscribe(topic, handler):
    command_handlers[topic] = handler
    mqttc.subscribe(topic)


def setup_discovery():
    for cfg in buttons:
        # Buttons are configured as MQTT device triggers
        mediolaid = cfg.get('mediola', DEFAULT_MEDIOLA_ID)
        mediola = get_mediola(mediolaid)
        if not mediola or not mediola.get('host'):
            log('Error: Could not find matching Mediola!')
            continue
        identifier = cfg['type'] + '_' + str(cfg['adr'])
        deviceid = "mediola_buttons_" + mediola['host'].replace(".", "")
        topic = config['mqtt']['topic'] + '/buttons/' + mediolaid + '/' + identifier

        payload = {
            "automation_type": "trigger",
            "topic": topic,
            "type": "button_short_press",
            "subtype": cfg.get('name', identifier),
            "device": device_payload(deviceid, "Mediola Button"),
        }
        publish_discovery('device_automation', mediolaid + '_' + identifier, payload)

    for blind in blinds:
        mediola = get_mediola(blind.mediolaid)
        if not mediola or not mediola.get('host'):
            log('Error: Could not find matching Mediola!')
            continue
        deviceid = "mediola_blinds_" + mediola['host'].replace(".", "")
        topic = blind_topic(blind)

        payload = {
            "command_topic": topic + "/set",
            "payload_open": "open",
            "payload_close": "close",
            "payload_stop": "stop",
            "device_class": blind.device_class,
            "unique_id": blind.unique_id,
            "name": blind.name,
            "device": device_payload(deviceid, "Mediola Blind"),
        }
        payload.update(availability_payload())

        if blind.tracks_position:
            payload["position_topic"] = topic + "/position"
            payload["set_position_topic"] = topic + "/set_position"
            payload["position_open"] = 100
            payload["position_closed"] = 0
            payload["state_topic"] = topic + "/state"
            payload["optimistic"] = False
            subscribe(topic + "/set_position",
                      lambda p, b=blind: handle_position_command(b, p))
        elif blind.type == 'ER':
            # Elero blinds report their state, everything else is optimistic
            payload["state_topic"] = topic + "/state"
            payload["optimistic"] = False
        else:
            payload["optimistic"] = True

        subscribe(topic + "/set", lambda p, b=blind: handle_cover_command(b, p))
        publish_discovery('cover', blind.unique_id, payload)

        if blind.type != 'ER':
            continue
        presets = []
        if blind.intermediate_position:
            presets.append(('intermediate', 'Intermediate Position'))
        if blind.ventilation_position:
            presets.append(('ventilation', 'Ventilation Position'))
        for action, label in presets:
            button_payload = {
                "command_topic": topic + "/" + action,
                "payload_press": "PRESS",
                "unique_id": blind.unique_id + '_' + action,
                "name": blind.name + ' ' + label,
                "device": device_payload(deviceid, "Mediola Blind"),
            }
            button_payload.update(availability_payload())
            subscribe(topic + "/" + action,
                      lambda p, b=blind, a=action: handle_preset_command(b, a))
            publish_discovery('button', blind.unique_id + '_' + action, button_payload)


def start_polling():
    global poll_thread
    with lock:
        if poll_thread is not None and poll_thread.is_alive():
            return
        poll_thread = threading.Thread(target=poll_states, daemon=True)
        poll_thread.start()


def poll_states():
    """Query the current state of all Elero blinds from the gateways."""
    interval = general.get('poll_interval', 0)
    while True:
        for mediola in iter_mediolas():
            mediolaid = get_mediola_id(mediola)
            states = parse_response(send_request(mediolaid, {'XC_FNC': 'GetStates'}))
            if not isinstance(states, list):
                continue
            for entry in states:
                if not isinstance(entry, dict) or entry.get('type') != 'ER':
                    continue
                handle_blind(entry.get('type'), str(entry.get('adr', '')).lower(),
                             str(entry.get('state', ''))[-2:].lower(), mediolaid)
        if not interval or interval <= 0:
            return
        time.sleep(interval)


def handle_button(packet_type, address, state, mediolaid):
    for cfg in buttons:
        if packet_type != cfg['type']:
            continue
        if str(cfg['adr']).lower() != address:
            continue
        if isinstance(config['mediola'], list) and cfg.get('mediola') != mediolaid:
            continue
        identifier = cfg['type'] + '_' + str(cfg['adr'])
        topic = config['mqtt']['topic'] + '/buttons/' + mediolaid + '/' + identifier
        mqttc.publish(topic, payload=state, retain=False)
        return True
    return False


def apply_er_state(blind, state):
    """Update the tracked position from a gateway status report."""
    if state in ER_STATE_OPEN:
        blind.halt()
        blind.set_position(100.0)
        return 'open'
    if state in ER_STATE_CLOSED:
        blind.halt()
        blind.set_position(0.0)
        return 'closed'
    if state in ER_STATE_OPENING:
        if blind.direction != 1:
            # Started externally - a move triggered by us keeps its target
            blind.begin_move(1, 100.0)
        return 'opening'
    if state in ER_STATE_CLOSING:
        if blind.direction != -1:
            blind.begin_move(-1, 0.0)
        return 'closing'
    if state in ER_STATE_STOPPED:
        blind.halt()
        return 'stopped'
    return 'unknown'


def handle_blind(packet_type, address, state, mediolaid):
    if packet_type != 'ER':
        return False
    for blind in blinds:
        if not blind.matches(packet_type, address):
            continue
        if isinstance(config['mediola'], list) and blind.mediolaid != mediolaid:
            continue
        with lock:
            event_state = apply_er_state(blind, state)
            publish_blind(blind, event_state=event_state)
        save_positions()
        return True
    return False


def get_mediolaid_by_address(addr):
    if not isinstance(config['mediola'], list):
        return DEFAULT_MEDIOLA_ID

    for mediola in config['mediola']:
        host = mediola['host']
        if host not in resolved_hosts:
            try:
                resolved_hosts[host] = socket.gethostbyname(host)
            except socket.error:
                resolved_hosts[host] = None
        if resolved_hosts[host] and addr[0] == resolved_hosts[host]:
            return get_mediola_id(mediola)

    return DEFAULT_MEDIOLA_ID

def handle_packet_v4(data, addr):
    try:
        data_dict = json.loads(data)
    except ValueError:
        return False

    mediolaid = get_mediolaid_by_address(addr)
    packet_type = data_dict['type']
    if handle_button(packet_type,
                     data_dict['data'][0:-2].lower(),
                     data_dict['data'][-2:].lower(),
                     mediolaid):
        return True
    return handle_blind(packet_type,
                        data_dict['data'][0:2].lower(),
                        data_dict['data'][-2:].lower(),
                        mediolaid)

def handle_packet_v6(data, addr):
    try:
        data_dict = json.loads(data)
    except ValueError:
        return False

    mediolaid = get_mediolaid_by_address(addr)
    packet_type = data_dict['type']
    address = data_dict['adr'].lower()
    state = data_dict['state'][-2:].lower()
    if handle_button(packet_type, address, state, mediolaid):
        return True
    return handle_blind(packet_type, address, state, mediolaid)


def create_sockets():
    ports = general.get('port', DEFAULT_LISTEN_PORTS)
    if not isinstance(ports, list):
        ports = [ports]
    sockets = []
    for port in ports:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            sock.bind(('', int(port)))
        except OSError as exc:
            log('Could not listen on UDP port %s: %s' % (port, exc))
            sock.close()
            continue
        log('Listening for gateway broadcasts on UDP port %s' % port)
        sockets.append(sock)
    if not sockets:
        log('No UDP port could be opened, exiting.')
        sys.exit(1)
    return sockets


# Setup MQTT connection
try:
    # paho-mqtt 2.x requires the callback API version to be selected
    mqttc = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1)
except AttributeError:
    mqttc = mqtt.Client()

mqttc.on_connect = on_connect
mqttc.on_subscribe = on_subscribe
mqttc.on_disconnect = on_disconnect
mqttc.on_message = on_message

if debug:
    print("Debugging messages enabled")
    mqttc.on_log = on_log    
    mqttc.on_publish = on_publish

if config['mqtt']['username'] and config['mqtt']['password']:
    mqttc.username_pw_set(config['mqtt']['username'], config['mqtt']['password'])
mqttc.will_set(availability_topic, payload='offline', retain=True)
try:
    mqttc.connect(config['mqtt']['host'], config['mqtt']['port'], 60)
except OSError as exc:
    print('Error connecting to MQTT (%s), will now quit.' % exc)
    sys.exit(1)
mqttc.loop_start()

load_positions()
threading.Thread(target=position_worker, daemon=True).start()

sockets = create_sockets()

while True:
    readable, _, _ = select.select(sockets, [], [])
    for sock in readable:
        data, addr = sock.recvfrom(1024)
        if debug:
            print('Received message: %s' % data)
            mqttc.publish(config['mqtt']['topic'], payload=data, retain=False)

        # For the v4 (and probably v5) gateways, the status packet starts
        # with '{XC_EVT}', but for the v6 it starts with 'STA:'.
        if data.startswith(b'{XC_EVT}'):
            data = data.replace(b'{XC_EVT}', b'')
            if not handle_packet_v4(data, addr):
                debug_log('Error handling v4 packet: %s' % data)
        elif data.startswith(b'STA:'):
            data = data.replace(b'STA:', b'')
            if not handle_packet_v6(data, addr):
                debug_log('Error handling v6 packet: %s' % data)
