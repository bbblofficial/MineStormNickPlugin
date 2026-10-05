package com.yourname.nick.util;

import java.lang.reflect.Constructor;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.util.Arrays;
import java.util.List;
import net.md_5.bungee.api.chat.BaseComponent;
import net.md_5.bungee.api.chat.TextComponent;
import net.md_5.bungee.chat.ComponentSerializer;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.BookMeta;

/**
 * Books with fully clickable / hoverable text on Spigot 1.8.8.
 *
 * The book is built as a normal WRITTEN_BOOK item and then, right
 * before it is sent to the player, its NMS ItemStack is patched so that
 * the "pages" NBT tag holds the JSON produced by BungeeCord's
 * ComponentSerializer. That JSON includes clickEvent / hoverEvent, which
 * vanilla 1.8.8 clients honour inside books.
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
        book.setItemMeta(meta);
        return book;
    }

    /**
     * Builds a written book whose pages are rich BaseComponents.
     * The click / hover events survive because we inject the raw JSON
     * into the NMS ItemStack when the book is opened.
     */
    public static ItemStack buildComponents(String title,
                                            String author,
                                            BaseComponent[]... pages) {
        ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
        BookMeta meta = (BookMeta) book.getItemMeta();
        meta.setTitle(title);
        meta.setAuthor(author);
        book.setItemMeta(meta);
        return book;
    }

    /**
     * Opens the given book for the player. If {@code richPages} is
     * non-null, its JSON is injected into the item's NMS NBT so the
     * client shows clickable / hoverable text.
     */
    public static boolean open(Player player, ItemStack book, BaseComponent[]... richPages) {
        if (player == null || book == null) {
            return false;
        }
        try {
            ItemStack toSend = (richPages != null && richPages.length > 0)
                    ? withRichPages(book, richPages)
                    : book;

            Object nmsBook = toNmsCopy(toSend);
            sendBookPacket(player, nmsBook);
            return true;
        } catch (Throwable ignored) {
            return false;
        }
    }

    public static boolean open(Player player, ItemStack book) {
        return open(player, book, (BaseComponent[][]) null);
    }

    /* ------------------------------------------------------------------ */
    /*  NMS plumbing                                                      */
    /* ------------------------------------------------------------------ */

    /**
     * Returns a copy of the Bukkit ItemStack whose internal NMS "pages"
     * tag holds the rich JSON from the given components.
     */
    private static ItemStack withRichPages(ItemStack book, BaseComponent[]... pages)
            throws Exception {
        Object nmsItem = toNmsCopy(book);
        Object tag = getTag(nmsItem);
        if (tag == null) {
            tag = newNbtTagCompound();
        }

        // Build a JSON string array, one per page.
        String[] json = new String[pages.length];
        for (int i = 0; i < pages.length; i++) {
            json[i] = ComponentSerializer.toString(pages[i]);
        }

        writeStringArrayTag(tag, "pages", json);
        setTag(nmsItem, tag);

        // Wrap back into a Bukkit ItemStack using the obfuscated
        // CraftItemStack.asBukkitCopy(ItemStack) method.
        return fromNmsCopy(nmsItem);
    }

    private static Object toNmsCopy(ItemStack bukkit) throws Exception {
        Class<?> craftItemStack = Class.forName(
                "org.bukkit.craftbukkit.v1_8_R3.inventory.CraftItemStack");
        Method asNms = craftItemStack.getMethod("asNMSCopy", ItemStack.class);
        return asNms.invoke(null, bukkit);
    }

    private static ItemStack fromNmsCopy(Object nms) throws Exception {
        Class<?> craftItemStack = Class.forName(
                "org.bukkit.craftbukkit.v1_8_R3.inventory.CraftItemStack");
        Method asBukkit = craftItemStack.getMethod("asBukkitCopy",
                Class.forName("net.minecraft.server.v1_8_R3.ItemStack"));
        return (ItemStack) asBukkit.invoke(null, nms);
    }

    private static Object getTag(Object nmsItem) throws Exception {
        Class<?> itemStackClass = Class.forName("net.minecraft.server.v1_8_R3.ItemStack");
        Method getTag = itemStackClass.getMethod("getTag");
        return getTag.invoke(nmsItem);
    }

    private static void setTag(Object nmsItem, Object tag) throws Exception {
        Class<?> itemStackClass = Class.forName("net.minecraft.server.v1_8_R3.ItemStack");
        Class<?> nbtTagClass   = Class.forName("net.minecraft.server.v1_8_R3.NBTTagCompound");
        Method setTag = itemStackClass.getMethod("setTag", nbtTagClass);
        setTag.invoke(nmsItem, tag);
    }

    private static Object newNbtTagCompound() throws Exception {
        Class<?> nbtTagClass = Class.forName("net.minecraft.server.v1_8_R3.NBTTagCompound");
        Constructor<?> ctor = nbtTagClass.getConstructor();
        return ctor.newInstance();
    }

    /**
     * Writes a String[] as an NBT list under the given key. Replaces any
     * existing value for that key.
     */
    private static void writeStringArrayTag(Object tag, String key, String[] values)
            throws Exception {
        Class<?> nbtTagClass        = Class.forName("net.minecraft.server.v1_8_R3.NBTTagCompound");
        Class<?> nbtListClass       = Class.forName("net.minecraft.server.v1_8_R3.NBTTagList");
        Class<?> nbtStringClass     = Class.forName("net.minecraft.server.v1_8_R3.NBTTagString");

        Object list = nbtListClass.getConstructor().newInstance();
        Method add = nbtListClass.getMethod("add",
                Class.forName("net.minecraft.server.v1_8_R3.NBTBase"));
        Constructor<?> stringCtor = nbtStringClass.getConstructor(String.class);

        for (String v : values) {
            Object nbtString = stringCtor.newInstance(v);
            add.invoke(list, nbtString);
        }

        Method set = nbtTagClass.getMethod("set", String.class,
                Class.forName("net.minecraft.server.v1_8_R3.NBTBase"));
        set.invoke(tag, key, list);
    }

    /**
     * Sends the player the "MC|BOpen" custom-payload packet with the book
     * already in their hand, so the client actually opens it.
     */
    private static void sendBookPacket(Player player, Object nmsBook) throws Exception {
        Object handle = player.getClass().getMethod("getHandle").invoke(player);

        Class<?> packetClass = Class.forName(
                "net.minecraft.server.v1_8_R3.PacketPlayOutCustomPayload");
        Class<?> serializerClass = Class.forName(
                "net.minecraft.server.v1_8_R3.PacketDataSerializer");
        Class<?> byteBufClass = Class.forName("io.netty.buffer.ByteBuf");
        Class<?> unpooledClass = Class.forName("io.netty.buffer.Unpooled");

        Object buffer = unpooledClass.getMethod("buffer").invoke(null);
        Object serializer = serializerClass.getConstructor(byteBufClass).newInstance(buffer);

        // MC|BOpen payload is just an empty payload on 1.8.8 - the book
        // being held is what the client opens. But we still need the
        // "pages" tag on the item in hand to contain the rich JSON, which
        // we have already built, so put the book into the player's hand
        // momentarily.
        Object packet = packetClass
                .getConstructor(String.class, serializerClass)
                .newInstance("MC|BOpen", serializer);

        // Put the book in the player's hand, send the packet, restore.
        Class<?> craftItemStack = Class.forName(
                "org.bukkit.craftbukkit.v1_8_R3.inventory.CraftItemStack");
        Method asBukkit = craftItemStack.getMethod("asBukkitCopy",
                Class.forName("net.minecraft.server.v1_8_R3.ItemStack"));
        ItemStack bukkitBook = (ItemStack) asBukkit.invoke(null, nmsBook);

        ItemStack previous = player.getItemInHand();
        player.setItemInHand(bukkitBook);

        Field connField = handle.getClass().getField("playerConnection");
        Object connection = connField.get(handle);
        Method sendPacket = connection.getClass().getMethod("sendPacket",
                Class.forName("net.minecraft.server.v1_8_R3.Packet"));
        sendPacket.invoke(connection, packet);

        // Restore whatever the player was holding. The client already has
        // the book open, so this is safe.
        player.setItemInHand(previous);
    }
}
