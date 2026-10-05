package com.yourname.nick.task;

import com.yourname.nick.MineStormNickPlugin;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.model.DisguiseProfile;
import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.TextComponent;
import net.md_5.bungee.chat.ComponentSerializer;
import org.bukkit.ChatColor;
import org.bukkit.entity.Player;

/**
 * Sends the "you are nicked" indicator through the real ACTION BAR only.
 *
 * <p>The Bungee ChatMessageType overload of Player.Spigot#sendMessage does
 * not exist on Spigot 1.8.8, so a previous revision fell back to the plain
 * chat overload and Bukkit deduplicated the message as "… (4)". This
 * version sends PacketPlayOutChat(component, (byte) 2) via NMS on 1.8.8
 * and uses the Bungee overload only when the server actually exposes it.</p>
 */
public final class ActionBarTask implements Runnable {

    /* ---------------- NMS handles (1.8.8) ---------------- */

    private static final Class<?>   CHAT_PACKET_CLASS;
    private static final Constructor<?> CHAT_PACKET_CTOR;
    private static final Method     GET_HANDLE;
    private static final Method     SEND_PACKET;
    private static final Method     FROM_JSON;
    private static final Field      CONNECTION_FIELD;

    static {
        Class<?> chatPacket = null;
        Constructor<?> ctor = null;
        Method getHandle = null;
        Method sendPacket = null;
        Method fromJson = null;
        Field  connField = null;
        try {
            chatPacket = Class.forName("net.minecraft.server.v1_8_R3.PacketPlayOutChat");
            Class<?> chatComp = Class.forName("net.minecraft.server.v1_8_R3.IChatBaseComponent");
            Class<?> packet   = Class.forName("net.minecraft.server.v1_8_R3.Packet");
            ctor = chatPacket.getConstructor(chatComp, byte.class);

            Class<?> craftPlayer =
                    Class.forName("org.bukkit.craftbukkit.v1_8_R3.entity.CraftPlayer");
            getHandle = craftPlayer.getMethod("getHandle");

            Class<?> entityPlayer =
                    Class.forName("net.minecraft.server.v1_8_R3.EntityPlayer");
            connField = entityPlayer.getField("playerConnection");

            Class<?> playerConn =
                    Class.forName("net.minecraft.server.v1_8_R3.PlayerConnection");
            sendPacket = playerConn.getMethod("sendPacket", packet);

            Class<?> serializer = Class.forName(
                    "net.minecraft.server.v1_8_R3.IChatBaseComponent$ChatSerializer");
            fromJson = serializer.getMethod("a", String.class);
        } catch (Throwable ignored) {
            // Not running on 1.8.8 - use the Bungee overload instead.
        }
        CHAT_PACKET_CLASS   = chatPacket;
        CHAT_PACKET_CTOR    = ctor;
        GET_HANDLE          = getHandle;
        SEND_PACKET         = sendPacket;
        FROM_JSON           = fromJson;
        CONNECTION_FIELD    = connField;
    }

    private final MineStormNickPlugin plugin;
    private final DisguiseRegistry registry;
    private final String indicator;
    private final boolean showWhenDormant;

    public ActionBarTask(MineStormNickPlugin plugin,
                         DisguiseRegistry registry,
                         String indicator,
                         boolean showWhenDormant) {
        this.plugin = plugin;
        this.registry = registry;
        this.indicator = ChatColor.translateAlternateColorCodes(
                '&', indicator == null ? "" : indicator);
        this.showWhenDormant = showWhenDormant;
    }

    @Override
    public void run() {
        if (this.indicator.isEmpty()) return;
        for (DisguiseProfile profile : this.registry.all()) {
            Player player = this.plugin.getServer().getPlayer(profile.realUuid());
            if (player == null || !player.isOnline()) continue;
            if (!profile.active() && !this.showWhenDormant) continue;
            try {
                sendActionBar(player, this.indicator);
            } catch (Throwable ignored) {
                // Never let one player's connection kill the task.
            }
        }
    }

    /** Sends {@code text} to the action bar. Never falls back to chat. */
    private static void sendActionBar(Player player, String text) {
        // Preferred path (Paper 1.12+): real Bungee action-bar overload.
        try {
            Class<?> spigot = Class.forName("org.bukkit.entity.Player$Spigot");
            Class<?> type   = Class.forName("net.md_5.bungee.api.ChatMessageType");
            Method m = spigot.getMethod("sendMessage", type, BaseComponent[].class);
            @SuppressWarnings({"unchecked", "rawtypes"})
            Object actionBar = Enum.valueOf(
                    (Class<? extends Enum>) type, "ACTION_BAR");
            m.invoke(player.spigot(), actionBar,
                    TextComponent.fromLegacyText(text));
            return;
        } catch (Throwable notAvailable) {
            // Fall through to the 1.8.8 packet path.
        }

        if (CHAT_PACKET_CTOR == null || GET_HANDLE == null
                || SEND_PACKET == null || CONNECTION_FIELD == null) {
            // Cannot reach the action bar on this fork; drop the update
            // silently instead of polluting chat.
            return;
        }

        try {
            Object handle = GET_HANDLE.invoke(player);
            String json = ComponentSerializer.toString(
                    TextComponent.fromLegacyText(text));
            Object component = FROM_JSON.invoke(null, json);
            Object packet = CHAT_PACKET_CTOR.newInstance(component, (byte) 2);
            Object connection = CONNECTION_FIELD.get(handle);
            SEND_PACKET.invoke(connection, packet);
        } catch (Throwable ignored) {
            // Silently drop on failure.
        }
    }
}
