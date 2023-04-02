#!/usr/bin/env python

from semantic_version import Version

versions = ['1.0.0', '2.0.0', '3.0.0-rc.1']
versions = [Version(x) for x in versions]
print(max(versions))
