#! /bin/bash

set -eu

#export THEME="hoge.yml"
#export ADOC="hoge.adoc"
#export OPDF="hoge.pdf"
export THEME="asciidoctor-pdf-theme.yml"
export ADOC="sample.adoc"
export OPDF="sample.pdf"

docker run \
    --rm \
    --network host \
    -v ./docs:/documents \
    -v ./fonts:/fonts \
    asciidoctor/docker-asciidoctor \
        asciidoctor-pdf \
            -n -q \
            -b pdf \
            -d article \
            --theme /documents/${THEME} \
            -a source-highlighter=rouge \
            -a rouge-style=monokai \
            -a pdf-fontsdir=/fonts \
            -a scripts=cjk \
            -a allow-uri-read \
            -r asciidoctor-kroki \
                -a kroki-server-url=http://localhost:8000 \
                -a kroki-default-format=png \
            /documents/${ADOC}
