FROM asciidoctor/docker-asciidoctor:latest

RUN apk add --no-cache \
  fontconfig ttf-dejavu \
  build-base cairo-dev pango-dev gdk-pixbuf-dev glib-dev libxml2-dev bison flex pkgconf \
&& gem install --no-document \
  asciidoctor-mathematical:0.3.5 \
  asciidoctor-kroki

RUN apk add --no-cache font-noto-cjk ttf-dejavu

ENV XDG_CACHE_HOME=/documents/.cache
ENV HOME=/documents

WORKDIR /documents
