FROM asciidoctor/docker-asciidoctor:1.72.0

WORKDIR /documents

RUN apk add --no-cache \
    font-noto-cjk \
    font-noto-cjk-extra \
    cmake \
    make \
    gcc \
    g++ \
    gmp-dev \
    lasem-dev \
    pango-dev \
    cairo-dev \
    openjdk11 \
    graphviz \
    ttf-dejavu

RUN gem install asciidoctor-pdf asciidoctor-diagram asciidoctor-mathematical asciidoctor-kroki

COPY . /documents/

CMD ["bash"]