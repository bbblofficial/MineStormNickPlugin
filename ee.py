#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fixer.py
========
Adds the missing Mojang authlib dependency to pom.xml and simplifies
PacketManager so it works with that dependency.

Run from repo root:

    python fixer.py
    git add -A
    git commit -m "fix: add authlib dependency for PacketManager"
    git push
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))
POM  = os.path.join(ROOT, "pom.xml")


# ---------------------------------------------------------------------------
#  1. Patch pom.xml  --  add mojang repo + authlib dependency
# ---------------------------------------------------------------------------

MOJANG_REPO = """        <repository>
            <id>mojang</id>
            <url>https://libraries.minecraft.net/</url>
        </repository>
"""

AUTHLIB_DEP = """        <dependency>
            <groupId>com.mojang</groupId>
            <artifactId>authlib</artifactId>
            <version>1.5.21</version>
            <scope>provided</scope>
        </dependency>
"""


def patch_pom():
    if not os.path.isfile(POM):
        print("[fixer] WARNING: pom.xml not found - skipping")
        return

    with open(POM, "r", encoding="utf-8") as fh:
        src = fh.read()

    changed = False

    # --- add the Mojang repository if it's not there yet ---------------
    if "<id>mojang</id>" not in src:
        # insert before </repositories>
        idx = src.find("</repositories>")
        if idx != -1:
            src = src[:idx] + MOJANG_REPO + "    " + src[idx:]
            changed = True
            print("[fixer] added <repository> mojang")

    # --- add the authlib dependency if it's not there yet --------------
    if "<artifactId>authlib</artifactId>" not in src:
        idx = src.find("</dependencies>")
        if idx != -1:
            src = src[:idx] + AUTHLIB_DEP + "    " + src[idx:]
            changed = True
            print("[fixer] added <dependency> com.mojang:authlib")

    if not changed:
        print("[fixer] pom.xml already up to date")
        return

    with open(POM, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(src)
    print("[fixer] pom.xml updated")


# ---------------------------------------------------------------------------
#  2. Simplify PacketManager so it no longer references
#     com.mojang.authlib.properties.Property directly
# ---------------------------------------------------------------------------

PACKETMANAGER_JAVA = r'''package com.yourname.nick.packet;

import com.mojang.authlib.GameProfile;
import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import java.util.UUID;
import org.bukkit.Bukkit;
import org.bukkit.entity.Player;

/**
 * Sends real 1.8.8 packets so that nick changes are visible immediately
 * in the tab list and in the world without a relog.
 */
public final class PacketManager {

    private final NickPlugin plugin;
    private final DisguiseRegistry registry;

    private Class<?> packetInfoClass;
    private Class<?> packetDestroyClass;
    private Class<?> packetSpawnClass;
    private Class<?> packetClass;
    private Class<?> enumPlayerInfoActionClass;
    private Class<?> entityPlayerClass;
    private Class<?> entityHumanClass;
    private Class<?> worldServerClass;
    private Class<?> playerConnectionClass;

    private Method getHandleMethod;
    private Field  playerConnectionField;
    private Method sendPacketMethod;
    private Method getProfileMethod;
    private Method setLocationMethod;
    private Method spawnInMethod;
    private Method getIdMethod;

    private boolean enabled = false;

    public PacketManager(NickPlugin plugin, DisguiseRegistry registry) {
        this.plugin = plugin;
        this.registry = registry;
    }

    /* ------------------------------------------------------------------ */
    /*  Lifecycle                                                         */
    /* ------------------------------------------------------------------ */

    public void load() {
        // nothing to do
    }

    public boolean enable() {
        try {
            String pkg = "net.minecraft.server.v1_8_R3.";
            this.packetInfoClass    = Class.forName(pkg + "PacketPlayOutPlayerInfo");
            this.packetDestroyClass = Class.forName(pkg + "PacketPlayOutEntityDestroy");
            this.packetSpawnClass   = Class.forName(pkg + "PacketPlayOutNamedEntitySpawn");
            this.packetClass        = Class.forName(pkg + "Packet");
            this.enumPlayerInfoActionClass =
                    Class.forName(pkg + "PacketPlayOutPlayerInfo$EnumPlayerInfoAction");
            this.entityPlayerClass  = Class.forName(pkg + "EntityPlayer");
            this.entityHumanClass   = Class.forName(pkg + "EntityHuman");
            this.worldServerClass   = Class.forName(pkg + "WorldServer");
            this.playerConnectionClass = Class.forName(pkg + "PlayerConnection");

            Class<?> craftPlayer = Class.forName(
                    "org.bukkit.craftbukkit.v1_8_R3.entity.CraftPlayer");
            this.getHandleMethod = craftPlayer.getMethod("getHandle");
            this.playerConnectionField = this.entityPlayerClass.getField("playerConnection");
            this.sendPacketMethod = this.playerConnectionClass.getMethod(
                    "sendPacket", this.packetClass);
            this.getProfileMethod = this.entityHumanClass.getMethod("getProfile");
            this.setLocationMethod = this.entityPlayerClass.getMethod(
                    "setLocation", double.class, double.class, double.class,
                    float.class, float.class);
            this.spawnInMethod = this.entityPlayerClass.getMethod(
                    "spawnIn", this.worldServerClass);
            this.getIdMethod = this.entityPlayerClass.getMethod("getId");

            this.enabled = true;
            this.plugin.getLogger().info("PacketManager: NMS 1.8.8 hooks installed.");
            return true;
        } catch (Throwable t) {
            this.plugin.getLogger().warning(
                    "PacketManager: could not install NMS hooks - " + t);
            this.enabled = false;
            return false;
        }
    }

    public void disable() {
        this.enabled = false;
    }

    /* ------------------------------------------------------------------ */
    /*  Public API                                                        */
    /* ------------------------------------------------------------------ */

    public void refreshTabList(Player target) {
        if (!this.enabled || target == null || !target.isOnline()) {
            return;
        }
        try {
            Object handle = this.getHandleMethod.invoke(target);
            Object profile = this.getProfileMethod.invoke(handle);

            String nick = resolveNick(target);
            if (nick == null || nick.isEmpty()) {
                return;
            }

            // Build a new GameProfile that only carries the new name.
            // We keep the same UUID so the client treats it as the same player.
            UUID uuid = target.getUniqueId();
            GameProfile copy = new GameProfile(uuid, nick);

            // Patch the entity's profile so that ADD_PLAYER sends the nick.
            Field profileField = findProfileField(handle.getClass());
            if (profileField == null) {
                return;
            }
            profileField.setAccessible(true);
            Object original = profileField.get(handle);
            profileField.set(handle, copy);

            List<Object> players = new ArrayList<Object>();
            players.add(handle);

            Object removeAction = enumAction("REMOVE_PLAYER");
            Object addAction    = enumAction("ADD_PLAYER");

            Object removePacket = buildInfoPacket(removeAction, players);
            Object addPacket    = buildInfoPacket(addAction, players);

            broadcast(removePacket);
            broadcast(addPacket);

            // restore
            profileField.set(handle, original);
        } catch (Throwable t) {
            this.plugin.getLogger().warning("refreshTabList failed: " + t);
        }
    }

    public void refreshNametag(Player target) {
        if (!this.enabled || target == null || !target.isOnline()) {
            return;
        }
        try {
            Object handle = this.getHandleMethod.invoke(target);
            int entityId = (Integer) this.getIdMethod.invoke(handle);

            Object destroyPacket = this.packetDestroyClass
                    .getConstructor(int[].class)
                    .newInstance((Object) new int[] { entityId });

            Object world = target.getWorld();
            Object worldServer = world.getClass()
                    .getMethod("getHandle").invoke(world);

            this.setLocationMethod.invoke(handle,
                    target.getLocation().getX(),
                    target.getLocation().getY(),
                    target.getLocation().getZ(),
                    target.getLocation().getYaw(),
                    target.getLocation().getPitch());

            this.spawnInMethod.invoke(handle, worldServer);

            Object spawnPacket = this.packetSpawnClass
                    .getConstructor(this.entityHumanClass)
                    .newInstance(handle);

            for (Player viewer : Bukkit.getOnlinePlayers()) {
                if (viewer.equals(target)) {
                    continue;
                }
                sendPacket(viewer, destroyPacket);
                sendPacket(viewer, spawnPacket);
            }

            refreshTabList(target);
        } catch (Throwable t) {
            this.plugin.getLogger().warning("refreshNametag failed: " + t);
        }
    }

    public void resendOwnEntry(Player player) {
        if (player == null || !player.isOnline()) {
            return;
        }
        refreshTabList(player);
        refreshNametag(player);
    }

    /* ------------------------------------------------------------------ */
    /*  Internal helpers                                                  */
    /* ------------------------------------------------------------------ */

    private String resolveNick(Player player) {
        DisguiseProfile profile = this.registry.get(player.getUniqueId()).orElse(null);
        return profile == null ? null : profile.nickname();
    }

    private Field findProfileField(Class<?> clazz) {
        Class<?> c = clazz;
        while (c != null) {
            try {
                Field f = c.getDeclaredField("profile");
                f.setAccessible(true);
                return f;
            } catch (NoSuchFieldException ignored) {
                c = c.getSuperclass();
            }
        }
        return null;
    }

    @SuppressWarnings({"unchecked", "rawtypes"})
    private Object enumAction(String name) throws Exception {
        return Enum.valueOf((Class<? extends Enum>) this.enumPlayerInfoActionClass, name);
    }

    private Object buildInfoPacket(Object action, List<Object> players)
            throws Exception {
        for (java.lang.reflect.Constructor<?> ctor
                : this.packetInfoClass.getConstructors()) {
            Class<?>[] params = ctor.getParameterTypes();
            if (params.length == 2
                    && params[0] == this.enumPlayerInfoActionClass
                    && Iterable.class.isAssignableFrom(params[1])) {
                return ctor.newInstance(action, players);
            }
        }
        if (!players.isEmpty()) {
            for (java.lang.reflect.Constructor<?> ctor
                    : this.packetInfoClass.getConstructors()) {
                Class<?>[] params = ctor.getParameterTypes();
                if (params.length == 2
                        && params[0] == this.enumPlayerInfoActionClass
                        && params[1] == this.entityPlayerClass) {
                    return ctor.newInstance(action, players.get(0));
                }
            }
        }
        throw new IllegalStateException("No usable PacketPlayOutPlayerInfo ctor");
    }

    private void broadcast(Object packet) throws Exception {
        for (Player online : Bukkit.getOnlinePlayers()) {
            sendPacket(online, packet);
        }
    }

    private void sendPacket(Player player, Object packet) throws Exception {
        Object handle = this.getHandleMethod.invoke(player);
        Object connection = this.playerConnectionField.get(handle);
        this.sendPacketMethod.invoke(connection, packet);
    }
}
'''


def write_packetmanager():
    for base in (os.path.join(ROOT, "src", "main", "java"),
                 os.path.join(ROOT)):
        path = os.path.join(base, "com", "yourname", "nick",
                            "packet", "PacketManager.java")
        if os.path.isfile(path):
            with open(path, "w", encoding="utf-8", newline="\n") as fh:
                fh.write(PACKETMANAGER_JAVA)
            print("[fixer] rewrote " + os.path.relpath(path, ROOT))
            return
    print("[fixer] WARNING: PacketManager.java not found")


def main():
    print("=" * 60)
    print(" NickSystem - authlib fix")
    print("=" * 60)
    patch_pom()
    write_packetmanager()
    print("=" * 60)
    print("[fixer] DONE. Now run:")
    print("[fixer]   git add -A")
    print("[fixer]   git commit -m 'fix: add authlib dependency'")
    print("[fixer]   git push")
    print("=" * 60)


if __name__ == "__main__":
    main()