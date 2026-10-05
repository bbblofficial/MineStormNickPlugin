package com.yourname.nick.util;

import java.lang.reflect.Constructor;
import java.lang.reflect.Method;
import java.util.ArrayList;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.Material;
import org.bukkit.entity.Player;
import org.bukkit.inventory.ItemStack;
import org.bukkit.inventory.meta.BookMeta;
import org.bukkit.inventory.meta.ItemMeta;

/**
 * Legacy book opener kept for source compatibility. The modern
 * implementation lives in VirtualBook; this class simply delegates.
 */
public final class BookOpener {

    private BookOpener() {
    }

    public static ItemStack build(String title, String author, List<String> legacyPages) {
        ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
        BookMeta meta = (BookMeta) book.getItemMeta();
        meta.setTitle(title);
        meta.setAuthor(author);
        List<String> clean = new ArrayList<String>();
        for (String p : legacyPages) {
            clean.add((p == null) ? "" : p);
        }
        meta.setPages(clean);
        book.setItemMeta((ItemMeta) meta);
        return book;
    }

    public static void open(Player player, ItemStack book) {
        if (player == null || book == null) {
            return;
        }
        if (VirtualBook.open(player, book)) {
            return;
        }
        ItemStack previous = player.getItemInHand();
        player.setItemInHand(book);
        player.sendMessage(ChatColor.GOLD + "Right-click the book to continue.");
        if (previous != null && previous.getType() != Material.AIR) {
            player.getInventory().addItem(previous);
        }
    }
}
