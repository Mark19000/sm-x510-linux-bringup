SHELL := /bin/bash
BUSYBOX ?=
VARIANT ?= wifi
FIRMWARE ?=

.PHONY: target check test fetch fetch-full image-tools report stock busybox initramfs build rescue-reference dtbo repack-reference reference-all avb-check osrc-u11 u11-initramfs u11-dtb-audit u11-modules-audit u11-preflight u11-offline clean

target:
	./scripts/target-info.sh

check:
	./scripts/check-host.sh

test:
	python3 -m unittest discover -s tests -v
	@for script in scripts/*.sh; do bash -n "$$script" || exit 1; done

fetch:
	DEVICE_VARIANT="$(VARIANT)" ./scripts/fetch-sources.sh --analysis --variant "$(VARIANT)"

fetch-full:
	DEVICE_VARIANT="$(VARIANT)" ./scripts/fetch-sources.sh --full --variant "$(VARIANT)"

image-tools:
	./scripts/fetch-image-tools.sh

report:
	DEVICE_VARIANT="$(VARIANT)" ./scripts/generate-reports.sh

stock:
	@test -n "$(FIRMWARE)" || { echo "Uso: make stock FIRMWARE=/ruta/firmware.zip" >&2; exit 2; }
	./scripts/extract-stock.sh "$(FIRMWARE)"

busybox:
	./scripts/build-busybox.sh

initramfs:
	DEVICE_VARIANT="$(VARIANT)" BUSYBOX="$(BUSYBOX)" ./scripts/build-initramfs.sh

build:
	DEVICE_VARIANT="$(VARIANT)" ./scripts/build-downstream.sh

rescue-reference:
	./scripts/build-rescue-in-lima.sh

dtbo:
	DEVICE_VARIANT="$(VARIANT)" ./scripts/build-dtbo.sh

repack-reference:
	./scripts/repack-reference-in-lima.sh

reference-all:
	./scripts/build-all-reference.sh

avb-check:
	./scripts/verify-avb-candidates.sh

osrc-u11:
	@test -n "$(OSRC_RELEASE)" || { echo "Uso: make osrc-u11 OSRC_RELEASE=/ruta/SM-X510.zip" >&2; exit 2; }
	OSRC_RELEASE="$(OSRC_RELEASE)" U11_BUILD="$${U11_BUILD:-inspect}" ./scripts/build-osrc-u11-in-lima.sh

u11-preflight:
	./scripts/u11-preflight.sh

u11-initramfs:
	./scripts/build-u11-initramfs-in-lima.sh

u11-dtb-audit:
	./scripts/u11-dtb-binary-audit.sh

u11-modules-audit:
	./scripts/u11-modules-audit.sh

u11-offline: u11-initramfs u11-dtb-audit u11-modules-audit u11-preflight
	@echo "Pipeline U11 offline verificado. Escritura física: NO-GO."

clean:
	@echo "Por seguridad no se borran fuentes. Elimina manualmente sólo el subdirectorio deseado de artifacts/."
