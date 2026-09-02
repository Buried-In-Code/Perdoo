#!/usr/bin/env bash

COLUMNS=120 pdm run perdoo --generate-help-preview
COLUMNS=120 pdm run perdoo archive --generate-help-preview
COLUMNS=120 pdm run perdoo archive comic-info --generate-help-preview
COLUMNS=120 pdm run perdoo archive metron-info --generate-help-preview
COLUMNS=120 pdm run perdoo archive remove --generate-help-preview
COLUMNS=120 pdm run perdoo archive tree --generate-help-preview
COLUMNS=120 pdm run perdoo clean --generate-help-preview
COLUMNS=120 pdm run perdoo convert --generate-help-preview
COLUMNS=120 pdm run perdoo rename --generate-help-preview
COLUMNS=120 pdm run perdoo settings --generate-help-preview
COLUMNS=120 pdm run perdoo sync --generate-help-preview
