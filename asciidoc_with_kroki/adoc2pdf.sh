#! /bin/bash

set -eu

# docker build -t asciidoctor-pdf-math .

#export THEME="hoge.yml"
#export ADOC="hoge.adoc"
#export OPDF="hoge.pdf"
export THEME="asciidoctor-pdf-theme.yml"
export ADOC="sample.adoc"
export OPDF="sample.pdf"

            #-a source-highlighter=rouge \
    #asciidoc_simple-asciidoctor \

docker run \
    --rm \
    --network host \
    -v ./docs:/documents \
    -v ./fonts:/fonts \
    asciidoctor-pdf-math \
        asciidoctor-pdf \
            -n -q \
            -b pdf \
            -d article \
            --theme /documents/${THEME} \
            -a stem=latexmath \
            -a docinfo=shared \
            -a docinfodir=/documets \
            -a rouge-style=monokai \
            -a pdf-fontsdir=/fonts \
            -a scripts=cjk \
            -r asciidoctor-mathematical \
            -r asciidoctor-kroki \
                -a kroki-server-url=http://localhost:8000 \
                -a kroki-default-format=png \
            /documents/${ADOC}

docker run \
    --rm \
    --network host \
    -v ./docs:/documents \
    -v ./fonts:/fonts \
    asciidoctor-pdf-math \
        asciidoctor \
            -n -q \
            -d article \
            -a stem=latexmath \
            -a docinfo=shared \
            -a docinfodir=/documets \
            -a rouge-style=monokai \
            -a scripts=cjk \
            -r asciidoctor-mathematical \
            -r asciidoctor-kroki \
                -a kroki-server-url=http://localhost:8000 \
                -a kroki-default-format=png \
            /documents/${ADOC}
