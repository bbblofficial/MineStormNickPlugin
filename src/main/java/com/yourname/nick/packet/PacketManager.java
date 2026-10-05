package com.yourname.nick.packet;

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
