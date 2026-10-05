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









public final class BookOpener
{
  public static ItemStack build(String title, String author, List<String> legacyPages) {
    ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
    BookMeta meta = (BookMeta)book.getItemMeta();
    meta.setTitle(title);
    meta.setAuthor(author);
    List<String> clean = new ArrayList<>();
    for (String p : legacyPages) clean.add((p == null) ? "" : p); 
    meta.setPages(clean);
    book.setItemMeta((ItemMeta)meta);
    return book;
  }

  
  public static void open(Player player, ItemStack book) {
    if (player == null || book == null)
      return;  if (openNms(player, book))
      return; 
    ItemStack previous = player.getItemInHand();
    player.setItemInHand(book);
    player.sendMessage(ChatColor.GOLD + "Right-click the book to continue.");

    
    if (previous != null && previous.getType() != Material.AIR) {
      player.getInventory().addItem(new ItemStack[] { previous });
    }
  }
  
  private static boolean openNms(Player player, ItemStack book) {
    try {
      Object packet;
      Class<?> packetClass = null;
      String[] candidates = { "net.minecraft.server.v1_8_R3.PacketPlayOutOpenBook", "net.minecraft.server.v1_8_R2.PacketPlayOutOpenBook", "net.minecraft.server.v1_8_R1.PacketPlayOutOpenBook" };



      
      for (String name : candidates) {
        
        try { packetClass = Class.forName(name);
          if (packetClass != null)
            break;  } catch (ClassNotFoundException classNotFoundException) {}
      } 
      
      if (packetClass == null) return false;
      
      Object handle = player.getClass().getMethod("getHandle", new Class[0]).invoke(player, new Object[0]);
      Object connection = handle.getClass().getField("playerConnection").get(handle);

      
      Object hand = null;
      try {
        Class<?> enumHandClass = Class.forName("net.minecraft.server.v1_8_R3.EnumHand");
        hand = enumHandClass.getEnumConstants()[0];
      } catch (Exception null) {}


      
      if (hand != null) {
        Constructor<?> ctor = packetClass.getConstructor(new Class[] { hand.getClass() });
        packet = ctor.newInstance(new Object[] { hand });
      } else {
        packet = packetClass.getConstructor(new Class[0]).newInstance(new Object[0]);
      } 
      
      Method sendPacket = connection.getClass().getMethod("sendPacket", new Class[] {
            Class.forName("net.minecraft.server.v1_8_R3.Packet") });
      sendPacket.invoke(connection, new Object[] { packet });
      return true;
    } catch (Throwable ignored) {
      return false;
    } 
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nic\\util\BookOpener.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */