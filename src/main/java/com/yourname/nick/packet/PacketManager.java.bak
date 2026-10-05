package com.yourname.nick.packet;

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
 * Sends real 1.8.8 packets so nick changes appear in the tab list
 * immediately, without a relog.
 *
 * On CarbonSpigot forks some NMS methods have a different signature, so
 * each optional hook (spawnIn, etc.) is resolved independently and a
 * failure of one does NOT prevent the whole manager from enabling.
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
    private Method getIdMethod;
    private Method setLocationMethod;   // optional
    private Method spawnInMethod;       // optional

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
            this.getIdMethod = this.entityPlayerClass.getMethod("getId");

            // --- optional hooks: do NOT fail if they are missing ----------
            this.setLocationMethod = tryGetMethod(this.entityPlayerClass,
                    "setLocation", double.class, double.class, double.class,
                    float.class, float.class);
            this.spawnInMethod = tryGetMethod(this.entityPlayerClass,
                    "spawnIn", this.worldServerClass);
            if (this.spawnInMethod == null) {
                // Some CarbonSpigot builds have spawnIn() with no args.
                this.spawnInMethod = tryGetMethod(this.entityPlayerClass, "spawnIn");
            }

            this.enabled = true;
            this.plugin.getLogger().info(
                    "PacketManager: hooks installed"
                    + (this.spawnInMethod == null
                            ? " (nametag respawn disabled on this server fork)"
                            : ""));
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

            UUID uuid = target.getUniqueId();
            GameProfile copy = new GameProfile(uuid, nick);

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

            profileField.set(handle, original);
        } catch (Throwable t) {
            this.plugin.getLogger().warning("refreshTabList failed: " + t);
        }
    }

    public void refreshNametag(Player target) {
        if (!this.enabled || target == null || !target.isOnline()) {
            return;
        }
        if (this.spawnInMethod == null) {
            // CarbonSpigot-style fork. Just update the tab list - the
            // in-world nametag is handled by TAB / other plugins there.
            refreshTabList(target);
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

            if (this.setLocationMethod != null) {
                this.setLocationMethod.invoke(handle,
                        target.getLocation().getX(),
                        target.getLocation().getY(),
                        target.getLocation().getZ(),
                        target.getLocation().getYaw(),
                        target.getLocation().getPitch());
            }

            // Handle both signatures: spawnIn(WorldServer) and spawnIn().
            if (this.spawnInMethod.getParameterTypes().length == 1) {
                this.spawnInMethod.invoke(handle, worldServer);
            } else {
                this.spawnInMethod.invoke(handle);
            }

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
            // Do not disable the whole manager for one failure.
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

    private static Method tryGetMethod(Class<?> clazz, String name, Class<?>... params) {
        try {
            Method m = clazz.getMethod(name, params);
            m.setAccessible(true);
            return m;
        } catch (NoSuchMethodException e) {
            return null;
        }
    }

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
