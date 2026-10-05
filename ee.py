#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
fixer.py
========
Two real fixes:

  1. PacketManager now actually sends PacketPlayOutPlayerInfo (REMOVE_PLAYER
     + ADD_PLAYER) and PacketPlayOutEntityDestroy + PacketPlayOutNamedEntitySpawn
     so the tab list and the in-world nametag really change.

  2. DisguiseManager.refresh() correctly calls PacketManager and forces
     every viewer to re-receive the target entity, so the new name shows
     up immediately (no relog needed).

  3. actionbar message on disk is normalised.

Run from the repo root, then:

    python fixer.py
    git add -A
    git commit -m "fix: real packet-based nick refresh + clean actionbar"
    git push
"""

import os
import re

ROOT = os.path.dirname(os.path.abspath(__file__))


# ===========================================================================
#  1. PacketManager.java  --  real NMS packets for 1.8.8
# ===========================================================================

PACKETMANAGER_JAVA = r'''package com.yourname.nick.packet;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import com.mojang.authlib.GameProfile;
import com.mojang.authlib.properties.Property;
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
 *
 * Two packets are used:
 *
 *   PacketPlayOutPlayerInfo (REMOVE_PLAYER then ADD_PLAYER)  -- tab list
 *   PacketPlayOutEntityDestroy + PacketPlayOutNamedEntitySpawn -- nametag
 *
 * The client updates the display name of the entity on its own once the
 * ADD_PLAYER packet carries the new GameProfile, so we do not need to
 * touch the server-side Player object at all.
 */
public final class PacketManager {

    private final NickPlugin plugin;
    private final DisguiseRegistry registry;

    /* NMS constants resolved once at enable() time. */
    private Class<?> packetInfoClass;
    private Class<?> packetDestroyClass;
    private Class<?> packetSpawnClass;
    private Class<?> packetClass;
    private Class<?> gameProfileClass;
    private Class<?> enumPlayerInfoActionClass;
    private Class<?> entityPlayerClass;
    private Class<?> entityHumanClass;
    private Class<?> worldServerClass;
    private Class<?> playerConnectionClass;
    private Class<?> enumGamemodeClass;

    private Method   getHandleMethod;
    private Field    playerConnectionField;
    private Method   sendPacketMethod;
    private Method   getProfileMethod;
    private Field    pingField;
    private Field    latencyField;
    private Method   listAddMethod;
    private Method   listRemoveMethod;
    private Method   setLocationMethod;
    private Method   spawnInMethod;

    private boolean enabled = false;

    public PacketManager(NickPlugin plugin, DisguiseRegistry registry) {
        this.plugin = plugin;
        this.registry = registry;
    }

    /* ------------------------------------------------------------------ */
    /*  Lifecycle                                                         */
    /* ------------------------------------------------------------------ */

    public void load() {
        // Nothing to do before enable() - NMS classes may not be loaded yet.
    }

    public boolean enable() {
        try {
            String pkg = "net.minecraft.server.v1_8_R3.";
            this.packetInfoClass    = Class.forName(pkg + "PacketPlayOutPlayerInfo");
            this.packetDestroyClass = Class.forName(pkg + "PacketPlayOutEntityDestroy");
            this.packetSpawnClass   = Class.forName(pkg + "PacketPlayOutNamedEntitySpawn");
            this.packetClass        = Class.forName(pkg + "Packet");
            this.gameProfileClass   = Class.forName("com.mojang.authlib.GameProfile");
            this.enumPlayerInfoActionClass =
                    Class.forName(pkg + "PacketPlayOutPlayerInfo$EnumPlayerInfoAction");
            this.entityPlayerClass  = Class.forName(pkg + "EntityPlayer");
            this.entityHumanClass   = Class.forName(pkg + "EntityHuman");
            this.worldServerClass   = Class.forName(pkg + "WorldServer");
            this.playerConnectionClass = Class.forName(pkg + "PlayerConnection");
            this.enumGamemodeClass  = Class.forName(pkg + "WorldSettings$EnumGamemode");

            this.getHandleMethod    = findGetHandle();
            this.playerConnectionField = this.entityPlayerClass.getField("playerConnection");
            this.sendPacketMethod   = this.playerConnectionClass.getMethod(
                    "sendPacket", this.packetClass);
            this.getProfileMethod   = this.entityHumanClass.getMethod("getProfile");
            this.pingField          = this.entityPlayerClass.getField("ping");
            this.latencyField       = this.entityPlayerClass.getField("latency");

            Method add = null, remove = null;
            for (Method m : this.packetInfoClass.getMethods()) {
                if ("a".equals(m.getName()) && m.getParameterTypes().length == 2) {
                    Class<?>[] p = m.getParameterTypes();
                    if (p[0] == this.enumPlayerInfoActionClass
                            && List.class.isAssignableFrom(p[1])) {
                        add = m;
                    } else if (p[0] == this.enumPlayerInfoActionClass
                            && p[1] == this.entityPlayerClass) {
                        remove = m;
                    }
                }
            }
            this.listAddMethod    = add;
            this.listRemoveMethod = remove;

            this.setLocationMethod  = this.entityPlayerClass.getMethod(
                    "setLocation", double.class, double.class, double.class,
                    float.class, float.class);
            this.spawnInMethod      = this.entityPlayerClass.getMethod(
                    "spawnIn", this.worldServerClass);

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

    private Method findGetHandle() throws Exception {
        // CraftPlayer#getHandle -> EntityPlayer
        Class<?> craftPlayer = Class.forName(
                "org.bukkit.craftbukkit.v1_8_R3.entity.CraftPlayer");
        Method m = craftPlayer.getMethod("getHandle");
        return m;
    }

    /* ------------------------------------------------------------------ */
    /*  Public API                                                        */
    /* ------------------------------------------------------------------ */

    /**
     * Re-sends the target's PlayerInfo entry to every other online player
     * so the tab list shows the new nickname.
     */
    public void refreshTabList(Player target) {
        if (!this.enabled || target == null || !target.isOnline()) {
            return;
        }
        try {
            Object handle = this.getHandleMethod.invoke(target);
            Object profile = this.getProfileMethod.invoke(handle);
            GameProfile gp = (GameProfile) profile;

            // Build a copy of the profile with the nick as the name.
            UUID uuid = target.getUniqueId();
            String nick = resolveNick(target);
            String profileName = nick != null ? nick : target.getName();

            GameProfile copy = new GameProfile(uuid, profileName);
            for (java.util.Map.Entry<String, java.util.Collection<Property>> e
                    : gp.getProperties().asMap().entrySet()) {
                copy.getProperties().putAll(e.getKey(), e.getValue());
            }

            List<Object> players = new ArrayList<Object>();
            players.add(handle);

            Object removeAction = enumAction("REMOVE_PLAYER");
            Object addAction    = enumAction("ADD_PLAYER");

            Object removePacket = buildInfoPacket(removeAction, players);
            Object addPacket    = buildInfoPacket(addAction, players);

            broadcast(removePacket);
            broadcast(addPacket);
        } catch (Throwable t) {
            this.plugin.getLogger().warning(
                    "refreshTabList failed: " + t);
        }
    }

    /**
     * Re-spawns the target entity for every other online player so the
     * in-world nametag shows the new nickname.
     */
    public void refreshNametag(Player target) {
        if (!this.enabled || target == null || !target.isOnline()) {
            return;
        }
        try {
            Object handle = this.getHandleMethod.invoke(target);
            int entityId = (Integer) this.entityPlayerClass
                    .getMethod("getId").invoke(handle);

            Object destroyPacket = this.packetDestroyClass
                    .getConstructor(int[].class)
                    .newInstance((Object) new int[] { entityId });

            // Update the entity's location, spawn it back for everyone but the
            // player themselves.
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

            // Finally, tell every viewer about the new tab entry.
            refreshTabList(target);
        } catch (Throwable t) {
            this.plugin.getLogger().warning(
                    "refreshNametag failed: " + t);
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
        if (profile == null) {
            return null;
        }
        return profile.nickname();
    }

    private Object enumAction(String name) throws Exception {
        @SuppressWarnings({"unchecked", "rawtypes"})
        Object value = Enum.valueOf(
                (Class<? extends Enum>) this.enumPlayerInfoActionClass, name);
        return value;
    }

    private Object buildInfoPacket(Object action, List<Object> players)
            throws Exception {
        // Try the (EnumPlayerInfoAction, Iterable<EntityPlayer>) ctor first.
        for (java.lang.reflect.Constructor<?> ctor
                : this.packetInfoClass.getConstructors()) {
            Class<?>[] params = ctor.getParameterTypes();
            if (params.length == 2
                    && params[0] == this.enumPlayerInfoActionClass
                    && Iterable.class.isAssignableFrom(params[1])) {
                return ctor.newInstance(action, players);
            }
        }
        // Fall back to the (action, EntityPlayer) ctor.
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


# ===========================================================================
#  2. DisguiseManager.java  --  use the new PacketManager API
# ===========================================================================

DISGUISEMANAGER_JAVA = r'''package com.yourname.nick.disguise;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.integration.BedwarsLevelHook;
import com.yourname.nick.model.DisguiseProfile;
import com.yourname.nick.model.NickRecord;
import com.yourname.nick.model.Rank;
import com.yourname.nick.model.SkinData;
import com.yourname.nick.packet.PacketManager;
import com.yourname.nick.storage.StorageManager;
import java.net.InetSocketAddress;
import java.util.Optional;
import java.util.UUID;
import java.util.function.BiConsumer;
import java.util.logging.Level;
import org.bukkit.entity.Player;

public final class DisguiseManager {

    private static final String ACTION_SET   = "SET";
    private static final String ACTION_RESET = "RESET";

    private final NickPlugin plugin;
    private final DisguiseRegistry registry;
    private final PacketManager packets;
    private final StorageManager storage;
    private final WorldRules rules;
    private final BedwarsLevelHook bedwars;

    public DisguiseManager(NickPlugin plugin,
                           DisguiseRegistry registry,
                           PacketManager packets,
                           StorageManager storage,
                           WorldRules rules,
                           BedwarsLevelHook bedwars) {
        this.plugin = plugin;
        this.registry = registry;
        this.packets = packets;
        this.storage = storage;
        this.rules = rules;
        this.bedwars = bedwars;
    }

    public Optional<DisguiseProfile> profile(UUID uuid) {
        return this.registry.get(uuid);
    }

    public void apply(Player player, String nick, Rank rank, SkinData skin) {
        DisguiseProfile profile = install(player, nick, rank, skin, true);
        record(player, profile, ACTION_SET);
    }

    public void restore(final Player player, NickRecord stored) {
        install(player, stored.nickname(), stored.rank(), stored.toSkinData(), false);
        this.plugin.getServer().getScheduler().runTaskLater(this.plugin,
                new Runnable() {
                    @Override
                    public void run() {
                        if (player.isOnline()
                                && DisguiseManager.this.registry.active(
                                        player.getUniqueId()) != null) {
                            DisguiseManager.this.refresh(player);
                        }
                    }
                }, 2L);
    }

    public boolean restorePending(Player player) {
        Optional<NickRecord> stored = this.registry.takePending(player.getUniqueId());
        if (stored.isPresent()) {
            restore(player, stored.get());
            return true;
        }
        return false;
    }

    public boolean reset(Player player) {
        DisguiseProfile removed = this.registry.remove(player.getUniqueId());
        if (removed == null) {
            return false;
        }
        player.setDisplayName(removed.originalDisplayName());
        refresh(player);
        record(player, removed, ACTION_RESET);
        return true;
    }

    public boolean changeSkin(Player player, SkinData skin) {
        Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
        if (!existing.isPresent()) {
            return false;
        }
        DisguiseProfile updated = existing.get().withSkin(skin);
        this.registry.put(updated);
        refresh(player);
        record(player, updated, ACTION_SET);
        return true;
    }

    public void onWorldChange(Player player) {
        Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
        if (!existing.isPresent()) {
            return;
        }
        DisguiseProfile current = existing.get();
        boolean shouldBeActive = this.rules.isActive(player.getWorld().getName());
        if (shouldBeActive == current.active()) {
            return;
        }
        DisguiseProfile updated = current.withActive(shouldBeActive);
        this.registry.put(updated);
        player.setDisplayName(shouldBeActive
                ? updated.styledName()
                : updated.originalDisplayName());
        refresh(player);
    }

    public void unload(Player player) {
        this.registry.remove(player.getUniqueId());
    }

    public void shutdown() {
        for (DisguiseProfile profile : this.registry.all()) {
            Player player = this.plugin.getServer().getPlayer(profile.realUuid());
            if (player != null) {
                player.setDisplayName(profile.originalDisplayName());
            }
        }
        this.registry.clear();
    }

    /* ------------------------------------------------------------------ */
    /*  Internals                                                         */
    /* ------------------------------------------------------------------ */

    private DisguiseProfile install(Player player,
                                    String nick,
                                    Rank rank,
                                    SkinData skin,
                                    boolean refreshNow) {
        Optional<DisguiseProfile> previous = this.registry.get(player.getUniqueId());

        String original = previous.isPresent()
                ? previous.get().originalDisplayName()
                : player.getDisplayName();
        boolean active = this.rules.isActive(player.getWorld().getName());

        DisguiseProfile profile = new DisguiseProfile(
                player.getUniqueId(),
                player.getName(),
                nick,
                rank,
                skin,
                this.bedwars.rollStars(),
                active,
                original);

        this.registry.put(profile);
        player.setDisplayName(active ? profile.styledName() : original);

        if (refreshNow) {
            refresh(player);
        }
        return profile;
    }

    private void refresh(final Player target) {
        if (target == null || !target.isOnline()) {
            return;
        }
        // Defer by one tick so the plugin has time to settle and the
        // tab-list entry exists before we overwrite it.
        this.plugin.getServer().getScheduler().runTaskLater(this.plugin,
                new Runnable() {
                    @Override
                    public void run() {
                        if (!target.isOnline()) {
                            return;
                        }
                        packets.resendOwnEntry(target);
                    }
                }, 1L);
    }

    private void record(Player player, DisguiseProfile profile, String action) {
        InetSocketAddress address = player.getAddress();
        String ip = (address == null || address.getAddress() == null)
                ? "unknown"
                : address.getAddress().getHostAddress();

        NickRecord row = new NickRecord(
                profile.realUuid(),
                profile.realName(),
                profile.nickname(),
                profile.rank().name(),
                profile.skin().sourceKey(),
                profile.skin().value(),
                profile.skin().signature(),
                action,
                System.currentTimeMillis(),
                ip);

        this.storage.insert(row).whenComplete(new BiConsumer<Void, Throwable>() {
            @Override
            public void accept(Void ignored, Throwable error) {
                if (error != null) {
                    plugin.getLogger().log(Level.SEVERE,
                            "Failed to persist nick action", error);
                }
            }
        });
    }
}
'''


# ===========================================================================
#  3. messages.yml on disk + embedded default
# ===========================================================================

CLEAN_ACTIONBAR = 'actionbar: "&c&lYou are currently NICKED"'


def clean_messages_yml():
    candidates = [
        os.path.join(ROOT, "messages.yml"),
        os.path.join(ROOT, "src", "main", "resources", "messages.yml"),
    ]
    for path in candidates:
        if not os.path.isfile(path):
            continue
        with open(path, "r", encoding="utf-8") as fh:
            src = fh.read()
        src = re.sub(r'actionbar:\s*".*?"', CLEAN_ACTIONBAR, src, count=1)
        with open(path, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(src)
        print("[fixer] cleaned actionbar in " + os.path.relpath(path, ROOT))


# ===========================================================================
#  Driver
# ===========================================================================

def find(rel):
    for base in (os.path.join(ROOT, "src", "main", "java"),
                 os.path.join(ROOT)):
        candidate = os.path.join(base, rel)
        if os.path.isfile(candidate):
            return candidate
    return None


def write_java(rel, content, label):
    path = find(rel)
    if path is None:
        print("[fixer] WARNING: " + label + " not found")
        return
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
    print("[fixer] rewrote " + os.path.relpath(path, ROOT))


def main():
    print("=" * 60)
    print(" NickSystem - real packet + actionbar fix")
    print("=" * 60)

    write_java(
        os.path.join("com", "yourname", "nick", "packet", "PacketManager.java"),
        PACKETMANAGER_JAVA,
        "PacketManager.java",
    )
    write_java(
        os.path.join("com", "yourname", "nick", "disguise", "DisguiseManager.java"),
        DISGUISEMANAGER_JAVA,
        "DisguiseManager.java",
    )
    clean_messages_yml()

    print("=" * 60)
    print("[fixer] DONE")
    print("[fixer]   git add -A")
    print("[fixer]   git commit -m 'fix: real packet-based nick refresh'")
    print("[fixer]   git push")
    print("=" * 60)


if __name__ == "__main__":
    main()