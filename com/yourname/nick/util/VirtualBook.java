package com.yourname.nick.util;

import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.TextComponent;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.BookMeta;
import org.bukkit.inventory.meta.ItemMeta;

/**
 * Builds and opens written books. Supports both legacy string pages and
 * rich BaseComponent pages (with click / hover events) which is what the
 * Hypixel-style nick GUI relies on.
 */
public final class VirtualBook {

    private VirtualBook() {
    }

    public static ItemStack build(String title, String author, String page1) {
        return build(title, author, Arrays.asList(page1));
    }

    public static ItemStack build(String title, String author, List<String> pages) {
        ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
        BookMeta meta = (BookMeta) book.getItemMeta();
        meta.setTitle(title);
        meta.setAuthor(author);
        meta.setPages(pages);
        book.setItemMeta((ItemMeta) meta);
        return book;
    }

    /**
     * Builds a book whose pages are rich chat components. Uses
     * {@code BookMeta.Spigot#setPages} if available so click / hover
     * events work on 1.8.8, otherwise falls back to legacy strings.
     */
    public static ItemStack buildComponents(String title,
                                            String author,
                                            BaseComponent[]... pages) {
        ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
        BookMeta meta = (BookMeta) book.getItemMeta();
        meta.setTitle(title);
        meta.setAuthor(author);

        boolean rich = false;
        try {
            Method spigotMethod = meta.getClass().getMethod("spigot");
            Object spigot = spigotMethod.invoke(meta);
            Method setPages = spigot.getClass().getMethod(
                    "setPages", BaseComponent[].class);
            setPages.invoke(spigot, (Object) pages);
            rich = true;
        } catch (Throwable ignored) {
            // Fall back to legacy below.
        }

        if (!rich) {
            List<String> legacy = new ArrayList<String>();
            for (BaseComponent[] page : pages) {
                legacy.add(TextComponent.toLegacyText(page));
            }
            meta.setPages(legacy);
        }

        book.setItemMeta((ItemMeta) meta);
        return book;
    }

    /** Opens the given book for the player via the 1.8 NMS book packet. */
    public static boolean open(Player player, ItemStack book) {
        if (player == null || book == null) {
            return false;
        }
        try {
            Object handle = player.getClass().getMethod("getHandle").invoke(player);

            Class<?> packetClass = null;
            String[] candidates = {
                    "net.minecraft.server.v1_8_R3.PacketPlayOutCustomPayload",
                    "net.minecraft.server.v1_8_R2.PacketPlayOutCustomPayload",
                    "net.minecraft.server.v1_8_R1.PacketPlayOutCustomPayload"
            };
            for (String name : candidates) {
                try {
                    packetClass = Class.forName(name);
                    break;
                } catch (ClassNotFoundException ignored) {
                }
            }
            if (packetClass == null) {
                return false;
            }

            Class<?> serializerClass = Class.forName(
                    "net.minecraft.server.v1_8_R3.PacketDataSerializer");
            Class<?> unpooledClass = Class.forName("io.netty.buffer.Unpooled");
            Object buffer = unpooledClass.getMethod("buffer").invoke(null);
            Object serializer = serializerClass
                    .getConstructor(Class.forName("io.netty.buffer.ByteBuf"))
                    .newInstance(buffer);

            Object packet = packetClass
                    .getConstructor(String.class, serializerClass)
                    .newInstance("MC|BOpen", serializer);

            Field connField = handle.getClass().getField("playerConnection");
            Object connection = connField.get(handle);
            Method sendPacket = connection.getClass().getMethod(
                    "sendPacket", Class.forName("net.minecraft.server.v1_8_R3.Packet"));

            ItemStack held = player.getItemInHand();
            player.setItemInHand(book);
            sendPacket.invoke(connection, packet);
            player.setItemInHand(held);
            return true;
        } catch (Throwable ignored) {
            return false;
        }
    }
}
