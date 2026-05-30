FROM openresty/openresty:1.25.3.1-3-alpine

RUN apk add --no-cache openssl curl bash bind-tools

# Install lua-resty-auto-ssl via opm (with perl, which opm requires)
# Fall back gracefully if OPM registry is unavailable
RUN apk add --no-cache perl \
    && /usr/local/openresty/bin/opm get ftnt/lua-resty-auto-ssl || true

# Fallback self-signed cert (always needed for HTTPS listener to start)
RUN openssl req -new -newkey rsa:2048 -days 3650 -nodes -x509 \
    -subj "/CN=openresty-fallback.local" \
    -keyout /etc/ssl/resty-auto-ssl-fallback.key \
    -out /etc/ssl/resty-auto-ssl-fallback.crt

# Create storage dir for auto-ssl
RUN mkdir -p /var/openresty-auto-ssl && chown nobody:nobody /var/openresty-auto-ssl

COPY nginx.conf /usr/local/openresty/nginx/conf/nginx.conf
COPY lua/ /usr/local/openresty/nginx/lua/

EXPOSE 80 443

CMD ["/usr/local/openresty/bin/openresty", "-g", "daemon off;"]
