FROM openresty/openresty:1.25.3.1-3-alpine

RUN apk add --no-cache openssl curl bash perl bind-tools \
    && /usr/local/openresty/bin/opm get GUI/lua-resty-auto-ssl

# Fallback cert so nginx can start before the first real LE cert is issued
RUN openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
    -subj "/CN=openresty-fallback.local" \
    -keyout /etc/ssl/resty-auto-ssl-fallback.key \
    -out /etc/ssl/resty-auto-ssl-fallback.crt

COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY lua/ /usr/local/openresty/nginx/lua/

EXPOSE 80 443

CMD ["/usr/local/openresty/bin/openresty", "-g", "daemon off;"]
