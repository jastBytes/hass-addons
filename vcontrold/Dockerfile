ARG BUILD_FROM
FROM $BUILD_FROM

RUN apk add --no-cache cmake make libxml2-dev linux-headers mosquitto-clients git jq iputils gcc musl-dev

RUN mkdir openv && cd openv && \
    git clone https://github.com/openv/vcontrold.git vcontrold-code && \
    cmake ./vcontrold-code -DVSIM=ON -DMANPAGES=OFF && \
    make && \
    make install

ADD config /etc/vcontrold/
COPY run.sh /
RUN chmod a+x /run.sh

ENTRYPOINT ["sh","/run.sh"]
