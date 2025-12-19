#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Test script: Build 16x16 joist module and export BOM to verify assembly compatibility."""

import codecs
import os

# Execute the joist module macro
macro_dir = os.path.dirname(__file__)
module_macro = os.path.join(macro_dir, "Joist_Module_2x12_16x16.FCMacro")
bom_macro = os.path.join(macro_dir, "export_bom.FCMacro")

print("[Test] Executing Joist_Module_2x12_16x16.FCMacro...")
with codecs.open(module_macro, "r", encoding="utf-8") as f:
    exec(compile(f.read(), module_macro, "exec"))

print("[Test] Executing export_bom.FCMacro...")
with codecs.open(bom_macro, "r", encoding="utf-8") as f:
    exec(compile(f.read(), bom_macro, "exec"))

print("[Test] BOM export complete. Check lumber_bom.csv for results.")
