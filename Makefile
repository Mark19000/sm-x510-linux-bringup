SHELL := /bin/bash
BUSYBOX ?=
VARIANT ?= wifi
FIRMWARE ?=

.PHONY: target check test verify-j2 verify-eze4-feasibility verify-c2-obs fetch fetch-full image-tools report stock busybox initramfs build rescue-reference dtbo repack-reference reference-all avb-check osrc-u11 u11-initramfs u11-dtb-audit u11-modules-audit u11-preflight u11-offline clean

target:
	./scripts/target-info.sh

check:
	./scripts/check-host.sh

test:
	python3 -m unittest discover -s tests -v
	@for script in scripts/*.sh; do bash -n "$$script" || exit 1; done

verify-j2:
	python3 -m unittest discover -s tools/rmg-eze4/tests -p 'test_phase_j2*.py' -v
	python3 tools/rmg-eze4/analysis/check_consistency.py
	python3 tools/rmg-eze4/analysis/verify_j2_closure.py
	python3 -m json.tool docs/rmg-eze4/phase_j2_observation_schema_v2.json >/dev/null
	python3 -m json.tool docs/rmg-eze4/phase_j2_event_grammar.json >/dev/null
	python3 -m json.tool tools/rmg-eze4/tests/fixtures/phase_j2_timeout_scenarios.json >/dev/null
	@echo "PASS: J2 closure gate"

verify-eze4-feasibility:
	python3 -m unittest discover -s tools/rmg-eze4/tests -p 'test_exploit_feasibility_audit.py' -v
	python3 tools/rmg-eze4/analysis/verify_exploit_feasibility.py
	@echo "PASS: EZE4 feasibility static audit gate"

verify-c2-obs:
	python3 -m unittest discover -s tools/rmg-eze4/tests -p 'test_c2_obs_01.py' -v
	python3 -m py_compile tools/rmg-eze4/c2_obs_01_collect.py tools/rmg-eze4/c2_obs_01_analyze.py
	python3 -m unittest discover -s tools/rmg-eze4/tests -p 'test_c2_dual_clock.py' -v
	python3 -m py_compile tools/rmg-eze4/c2_dual_clock_analyze.py
	clang -std=c11 -Wall -Wextra -Wpedantic -Werror -fsyntax-only -DCLOCK_BOOTTIME=7 tools/rmg-eze4/c2_dual_clock_observer.c
	@echo "PASS: C2-OBS-01 offline integrity gate"

fetch:
	DEVICE_VARIANT="$(VARIANT)" ./scripts/fetch-sources.sh --analysis --variant "$(VARIANT)"

fetch-full:
	DEVICE_VARIANT="$(VARIANT)" ./scripts/fetch-sources.sh --full --variant "$(VARIANT)"

image-tools:
	./scripts/fetch-image-tools.sh

report:
	DEVICE_VARIANT="$(VARIANT)" ./scripts/generate-reports.sh

stock:
	@test -n "$(FIRMWARE)" || { echo "Usage: make stock FIRMWARE=/path/to/firmware.zip" >&2; exit 2; }
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
	@test -n "$(OSRC_RELEASE)" || { echo "Usage: make osrc-u11 OSRC_RELEASE=/path/to/SM-X510.zip" >&2; exit 2; }
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
	@echo "U11 offline pipeline verified. Physical flash: NO-GO."

clean:
	@echo "For safety, sources are not deleted. Manually delete only the desired subdirectory from artifacts/."
