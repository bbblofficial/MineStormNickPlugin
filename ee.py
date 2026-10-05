#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fixer.py — Full repair
======================
Converts the flat JAR-extracted layout into a proper Maven project and
makes the GitHub Actions workflow fail loudly if the JAR ends up empty.

Run from the repo root (the folder that contains `com/`, `plugin.yml`,
`config.yml`, `messages.yml`, `names.yml`):

    python fixer.py
    git add -A
    git commit -m "fix: proper Maven layout + verified build"
    git push
"""

import os
import re
import shutil

ROOT = os.path.dirname(os.path.abspath(__file__))


# ===========================================================================
#  Paths
# ===========================================================================

JAVA_SRC      = os.path.join(ROOT, "com")
JAVA_DST_DIR  = os.path.join(ROOT, "src", "main", "java")
JAVA_DST      = os.path.join(JAVA_DST_DIR, "com")

RES_DST       = os.path.join(ROOT, "src", "main", "resources")
RES_FILES     = ["plugin.yml", "config.yml", "messages.yml", "names.yml"]

META_DIR      = os.path.join(ROOT, "META-INF")
POM_ROOT      = os.path.join(ROOT, "pom.xml")
GITIGNORE     = os.path.join(ROOT, ".gitignore")
WORKFLOW_DIR  = os.path.join(ROOT, ".github", "workflows")
WORKFLOW_FILE = os.path.join(WORKFLOW_DIR, "build.yml")


# ===========================================================================
#  Helpers
# ===========================================================================

def log(msg):
    print("[fixer] " + msg)


def warn(msg):
    print("[fixer] WARNING: " + msg)


def read(path):
    with open(path, "r", encoding="utf-8") as fh:
        return fh.read()


def write(path, content):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)


def rmtree(path):
    if os.path.isdir(path):
        shutil.rmtree(path)


# ===========================================================================
#  STEP 1 — move com/ -> src/main/java/com/
# ===========================================================================

def move_java_sources():
    if not os.path.isdir(JAVA_SRC):
        if os.path.isdir(JAVA_DST):
            log("java sources already in src/main/java/com/ — skipping")
            return
        warn("no com/ folder found — nothing to move")
        return

    os.makedirs(JAVA_DST_DIR, exist_ok=True)
    if os.path.exists(JAVA_DST):
        rmtree(JAVA_DST)

    shutil.move(JAVA_SRC, JAVA_DST)
    log("moved  com/  ->  src/main/java/com/")


# ===========================================================================
#  STEP 2 — move yml resources
# ===========================================================================

def move_resources():
    os.makedirs(RES_DST, exist_ok=True)
    moved = 0
    for name in RES_FILES:
        src = os.path.join(ROOT, name)
        if not os.path.isfile(src):
            continue
        shutil.move(src, os.path.join(RES_DST, name))
        log("moved  %s  ->  src/main/resources/%s" % (name, name))
        moved += 1
    if moved == 0:
        log("no resources to move (they're already in src/main/resources/)")


# ===========================================================================
#  STEP 3 — drop META-INF (jd-gui junk)
# ===========================================================================

def drop_meta_inf():
    if os.path.isdir(META_DIR):
        rmtree(META_DIR)
        log("removed META-INF/")


# ===========================================================================
#  STEP 4 — drop target/ so we start clean
# ===========================================================================

def clean_target():
    rmtree(os.path.join(ROOT, "target"))
    log("removed old target/")


# ===========================================================================
#  STEP 5 — write proper pom.xml
# ===========================================================================

POM_XML = r'''<?xml version="1.0" encoding="UTF-8"?>
<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0
                             http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>com.yourname</groupId>
    <artifactId>nicksystem</artifactId>
    <version>1.0.0</version>
    <packaging>jar</packaging>
    <name>NickSystem</name>
    <description>Nickname system for Spigot/Paper 1.8.8 (built for JDK 8+).</description>

    <properties>
        <maven.compiler.source>1.8</maven.compiler.source>
        <maven.compiler.target>1.8</maven.compiler.target>
        <maven.compiler.release>8</maven.compiler.release>
        <project.build.sourceEncoding>UTF-8</project.build.sourceEncoding>
        <spigot.version>1.8.8-R0.1-SNAPSHOT</spigot.version>
        <placeholderapi.version>2.11.5</placeholderapi.version>
    </properties>

    <repositories>
        <repository>
            <id>spigot-repo</id>
            <url>https://hub.spigotmc.org/nexus/content/repositories/snapshots/</url>
        </repository>
        <repository>
            <id>md-5-repo</id>
            <url>https://repo.md-5.net/content/groups/public/</url>
        </repository>
        <repository>
            <id>codemc-repo</id>
            <url>https://repo.codemc.io/repository/maven-public/</url>
        </repository>
        <repository>
            <id>placeholderapi</id>
            <url>https://repo.extendedclip.com/content/repositories/placeholderapi/</url>
        </repository>
    </repositories>

    <dependencies>
        <dependency>
            <groupId>org.spigotmc</groupId>
            <artifactId>spigot-api</artifactId>
            <version>${spigot.version}</version>
            <scope>provided</scope>
        </dependency>
        <dependency>
            <groupId>me.clip</groupId>
            <artifactId>placeholderapi</artifactId>
            <version>${placeholderapi.version}</version>
            <scope>provided</scope>
        </dependency>

        <!-- Bundled at runtime -->
        <dependency>
            <groupId>org.xerial</groupId>
            <artifactId>sqlite-jdbc</artifactId>
            <version>3.44.1.0</version>
            <scope>compile</scope>
        </dependency>
        <dependency>
            <groupId>mysql</groupId>
            <artifactId>mysql-connector-java</artifactId>
            <version>8.0.33</version>
            <scope>compile</scope>
        </dependency>
        <dependency>
            <groupId>com.google.code.gson</groupId>
            <artifactId>gson</artifactId>
            <version>2.10.1</version>
            <scope>compile</scope>
        </dependency>
    </dependencies>

    <build>
        <finalName>${project.name}-${project.version}</finalName>

        <resources>
            <resource>
                <directory>src/main/resources</directory>
                <filtering>true</filtering>
                <includes>
                    <include>plugin.yml</include>
                </includes>
            </resource>
            <resource>
                <directory>src/main/resources</directory>
                <filtering>false</filtering>
                <excludes>
                    <exclude>plugin.yml</exclude>
                </excludes>
            </resource>
        </resources>

        <plugins>
            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-compiler-plugin</artifactId>
                <version>3.13.0</version>
                <configuration>
                    <source>1.8</source>
                    <target>1.8</target>
                    <release>8</release>
                    <encoding>UTF-8</encoding>
                </configuration>
            </plugin>

            <plugin>
                <groupId>org.apache.maven.plugins</groupId>
                <artifactId>maven-shade-plugin</artifactId>
                <version>3.5.1</version>
                <executions>
                    <execution>
                        <phase>package</phase>
                        <goals>
                            <goal>shade</goal>
                        </goals>
                        <configuration>
                            <createDependencyReducedPom>false</createDependencyReducedPom>
                            <filters>
                                <filter>
                                    <artifact>*:*</artifact>
                                    <excludes>
                                        <exclude>META-INF/*.SF</exclude>
                                        <exclude>META-INF/*.DSA</exclude>
                                        <exclude>META-INF/*.RSA</exclude>
                                        <exclude>META-INF/MANIFEST.MF</exclude>
                                        <exclude>module-info.class</exclude>
                                    </excludes>
                                </filter>
                            </filters>
                        </configuration>
                    </execution>
                </executions>
            </plugin>
        </plugins>
    </build>
</project>
'''


def write_pom():
    if os.path.isfile(POM_ROOT):
        existing = read(POM_ROOT)
        # already a real pom (not the tiny META-INF one)?
        if "<build>" in existing and "<dependencies>" in existing:
            log("pom.xml already looks valid — leaving it alone")
            return
        log("overwriting invalid pom.xml")
    write(POM_ROOT, POM_XML)
    log("wrote proper pom.xml at repo root")


# ===========================================================================
#  STEP 6 — .gitignore
# ===========================================================================

GITIGNORE_CONTENT = r'''# Build output
target/
*.jar
!lib/*.jar

# IDE
.idea/
*.iml
.vscode/
.settings/
.project
.classpath

# OS
.DS_Store
Thumbs.db

# Runtime files the plugin generates
nick.db
skincache/
logs/

# Python helper (safe to keep the file, ignore pycache)
__pycache__/
*.pyc
'''


def write_gitignore():
    if os.path.isfile(GITIGNORE):
        existing = read(GITIGNORE)
        if "target/" in existing:
            log(".gitignore already covers target/ — leaving it")
            return
    write(GITIGNORE, GITIGNORE_CONTENT)
    log("wrote .gitignore")


# ===========================================================================
#  STEP 7 — workflow with verification step
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

      - name: Show project layout
        run: |
          echo "=== repo root ==="
          ls -la
          echo "=== src/main/java ==="
          find src/main/java -maxdepth 4 -type d || true
          echo "=== src/main/resources ==="
          ls -la src/main/resources || true

      - name: Build with Maven
        run: mvn -B --no-transfer-progress clean package

      - name: Verify JAR contents (fail if empty)
        run: |
          set -e
          JAR=$(ls target/NickSystem-*.jar | head -n1)
          SIZE=$(stat -c%s "$JAR")
          CLASSES=$(unzip -l "$JAR" | grep -c '\.class$' || true)
          echo "JAR:     $JAR"
          echo "Size:    $SIZE bytes"
          echo "Classes: $CLASSES"
          if [ "$SIZE" -lt 20000 ]; then
            echo "::error::JAR is suspiciously small ($SIZE bytes). Sources were likely not compiled."
            unzip -l "$JAR"
            exit 1
          fi
          if [ "$CLASSES" -lt 10 ]; then
            echo "::error::Only $CLASSES .class files found — sources are missing from src/main/java."
            unzip -l "$JAR"
            exit 1
          fi
          echo "OK: JAR contains $CLASSES classes, $SIZE bytes."

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


def write_workflow():
    os.makedirs(WORKFLOW_DIR, exist_ok=True)
    write(WORKFLOW_FILE, BUILD_YML)
    log("wrote .github/workflows/build.yml (with JAR verification)")


# ===========================================================================
#  STEP 8 — post-check
# ===========================================================================

def sanity_check():
    print("=" * 60)
    print("[fixer] Sanity check")
    print("=" * 60)

    java_dir = os.path.join(ROOT, "src", "main", "java", "com")
    if not os.path.isdir(java_dir):
        warn("src/main/java/com/  NOT found — sources are still flat!")
    else:
        count = 0
        for dirpath, _dirnames, filenames in os.walk(java_dir):
            count += sum(1 for f in filenames if f.endswith(".java"))
        log("src/main/java/com/ contains %d .java files" % count)

    res_dir = os.path.join(ROOT, "src", "main", "resources")
    if not os.path.isdir(res_dir):
        warn("src/main/resources/ NOT found")
    else:
        for name in RES_FILES:
            marker = "OK " if os.path.isfile(os.path.join(res_dir, name)) else "MISS"
            log("  [%s] src/main/resources/%s" % (marker, name))

    log("pom.xml present at root: %s" % os.path.isfile(POM_ROOT))
    log(".gitignore present:      %s" % os.path.isfile(GITIGNORE))
    log("workflow present:        %s" % os.path.isfile(WORKFLOW_FILE))


# ===========================================================================
#  Driver
# ===========================================================================

def main():
    print("=" * 60)
    print(" NickSystem — full repository fixer")
    print("=" * 60)
    clean_target()
    move_java_sources()
    move_resources()
    drop_meta_inf()
    write_pom()
    write_gitignore()
    write_workflow()
    sanity_check()

    print("=" * 60)
    print("[fixer] DONE. Now run:")
    print("[fixer]   git add -A")
    print("[fixer]   git commit -m 'fix: proper Maven layout + verified build'")
    print("[fixer]   git push")
    print("=" * 60)


if __name__ == "__main__":
    main()