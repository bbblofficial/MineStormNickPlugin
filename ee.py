#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fixer.py
========
Adds the GitHub Actions workflow (.github/workflows/build.yml) to the
repository and makes sure everything the workflow needs is in place.

What it does
------------
1. Creates .github/workflows/build.yml
2. Copies pom.xml from META-INF/maven/<group>/<artifact>/pom.xml to the
   repo root, if it isn't there yet (GitHub Actions needs a root pom.xml)
3. Detects whether sources are in a Maven layout (src/main/java) or the
   flat JAR-extracted layout (com/ at the root) and warns accordingly.

Run from the repo root, then:

    git add -A
    git commit -m "ci: add GitHub Actions build workflow"
    git push
"""

import os
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))

WORKFLOW_DIR  = os.path.join(ROOT, ".github", "workflows")
WORKFLOW_FILE = os.path.join(WORKFLOW_DIR, "build.yml")


# ===========================================================================
#  Workflow definition
# ===========================================================================

BUILD_YML = r'''name: Build NickSystem

on:
  push:
    branches: [ main, master, develop ]
    tags:     [ 'v*' ]
  pull_request:
    branches: [ main, master, develop ]
  workflow_dispatch:

permissions:
  contents: read

jobs:
  build:
    name: Build with JDK 8
    runs-on: ubuntu-latest

    steps:
      - name: Checkout repository
        uses: actions/checkout@v4

      - name: Set up JDK 8 (Temurin)
        uses: actions/setup-java@v4
        with:
          distribution: 'temurin'
          java-version: '8'

      - name: Cache Maven repository
        uses: actions/cache@v4
        with:
          path: ~/.m2/repository
          key: ${{ runner.os }}-maven-${{ hashFiles('**/pom.xml') }}
          restore-keys: |
            ${{ runner.os }}-maven-

      - name: Configure Maven settings
        run: |
          mkdir -p ~/.m2
          cat > ~/.m2/settings.xml <<'EOF'
          <settings xmlns="http://maven.apache.org/SETTINGS/1.0.0"
                    xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
                    xsi:schemaLocation="http://maven.apache.org/SETTINGS/1.0.0
                                        https://maven.apache.org/xsd/settings-1.0.0.xsd">
            <profiles>
              <profile>
                <id>allow-http</id>
                <repositories>
                  <repository>
                    <id>spigot-repo</id>
                    <url>https://hub.spigotmc.org/nexus/content/repositories/snapshots/</url>
                    <releases><enabled>false</enabled></releases>
                    <snapshots><enabled>true</enabled></snapshots>
                  </repository>
                </repositories>
              </profile>
            </profiles>
            <activeProfiles>
              <activeProfile>allow-http</activeProfile>
            </activeProfiles>
          </settings>
          EOF

      - name: Build with Maven
        run: mvn -B --no-transfer-progress clean package

      - name: Show target contents
        run: ls -la target/

      - name: Upload JAR artifact
        uses: actions/upload-artifact@v4
        with:
          name: NickSystem-jar
          path: target/NickSystem-*.jar
          if-no-files-found: error
          retention-days: 30

  release:
    name: Publish Release
    needs: build
    if: startsWith(github.ref, 'refs/tags/v')
    runs-on: ubuntu-latest
    permissions:
      contents: write

    steps:
      - name: Download built JAR
        uses: actions/download-artifact@v4
        with:
          name: NickSystem-jar
          path: ./release

      - name: Create GitHub Release
        uses: softprops/action-gh-release@v2
        with:
          files: ./release/NickSystem-*.jar
          generate_release_notes: true
'''


# ===========================================================================
#  Helpers
# ===========================================================================

def ensure_dir(path):
    if not os.path.isdir(path):
        os.makedirs(path)


def write_file(path, content):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


# ===========================================================================
#  Step 1 - write the workflow file
# ===========================================================================

def add_workflow():
    ensure_dir(WORKFLOW_DIR)
    write_file(WORKFLOW_FILE, BUILD_YML)
    print("[fixer] created .github/workflows/build.yml")


# ===========================================================================
#  Step 2 - make sure pom.xml is at the repo root
# ===========================================================================

def ensure_root_pom():
    root_pom = os.path.join(ROOT, "pom.xml")
    if os.path.isfile(root_pom):
        print("[fixer] pom.xml already present at repo root")
        return True

    # Look for the pom that jd-gui put inside META-INF/maven/...
    meta_maven = os.path.join(ROOT, "META-INF", "maven")
    if os.path.isdir(meta_maven):
        for group in os.listdir(meta_maven):
            group_dir = os.path.join(meta_maven, group)
            if not os.path.isdir(group_dir):
                continue
            for artifact in os.listdir(group_dir):
                candidate = os.path.join(group_dir, artifact, "pom.xml")
                if os.path.isfile(candidate):
                    shutil.copyfile(candidate, root_pom)
                    print("[fixer] copied pom.xml from META-INF/maven/... to root")
                    return True

    print("[fixer] WARNING: no pom.xml found. The workflow will fail.")
    print("[fixer]          Create a proper pom.xml at the repo root first")
    print("[fixer]          (see the project's instructions).")
    return False


# ===========================================================================
#  Step 3 - detect the layout (flat vs Maven) and warn if needed
# ===========================================================================

def detect_layout():
    flat_java   = os.path.isdir(os.path.join(ROOT, "com"))
    maven_java  = os.path.isdir(os.path.join(ROOT, "src", "main", "java"))
    maven_res   = os.path.isdir(os.path.join(ROOT, "src", "main", "resources"))

    if maven_java and maven_res:
        print("[fixer] layout: Maven standard (src/main/java + src/main/resources)")
        return "maven"

    if flat_java:
        print("[fixer] layout: flat JAR-extracted (com/ at repo root)")
        print("[fixer] WARNING: Maven cannot build the flat layout.")
        print("[fixer]          Run restructure.py first to convert to Maven layout.")
        return "flat"

    print("[fixer] layout: unknown (no com/ and no src/main/java found)")
    return "unknown"


# ===========================================================================
#  Main
# ===========================================================================

def main():
    print("=" * 60)
    print(" NickSystem build.yml fixer")
    print("=" * 60)

    add_workflow()
    have_pom = ensure_root_pom()
    layout = detect_layout()

    print("=" * 60)
    if layout == "flat":
        print("[fixer] Next step: run  python restructure.py")
        print("[fixer] Then:     git add -A && git commit -m 'ci: add workflow' && git push")
    elif have_pom:
        print("[fixer] DONE. Now run:")
        print("[fixer]   git add -A")
        print("[fixer]   git commit -m 'ci: add GitHub Actions build workflow'")
        print("[fixer]   git push")
    else:
        print("[fixer] Workflow written, but pom.xml is missing.")
        print("[fixer] Add a proper pom.xml at the repo root before pushing.")
    print("=" * 60)


if __name__ == "__main__":
    main()