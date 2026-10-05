/*    */ package com.yourname.nick.util;
/*    */ 
/*    */ import java.lang.reflect.Constructor;
/*    */ import java.lang.reflect.Method;
/*    */ import java.util.ArrayList;
/*    */ import java.util.List;
/*    */ import org.bukkit.ChatColor;
/*    */ import org.bukkit.Material;
/*    */ import org.bukkit.entity.Player;
/*    */ import org.bukkit.inventory.ItemStack;
/*    */ import org.bukkit.inventory.meta.BookMeta;
/*    */ import org.bukkit.inventory.meta.ItemMeta;
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class BookOpener
/*    */ {
/*    */   public static ItemStack build(String title, String author, List<String> legacyPages) {
/* 25 */     ItemStack book = new ItemStack(Material.WRITTEN_BOOK);
/* 26 */     BookMeta meta = (BookMeta)book.getItemMeta();
/* 27 */     meta.setTitle(title);
/* 28 */     meta.setAuthor(author);
/* 29 */     List<String> clean = new ArrayList<>();
/* 30 */     for (String p : legacyPages) clean.add((p == null) ? "" : p); 
/* 31 */     meta.setPages(clean);
/* 32 */     book.setItemMeta((ItemMeta)meta);
/* 33 */     return book;
/*    */   }
/*    */ 
/*    */   
/*    */   public static void open(Player player, ItemStack book) {
/* 38 */     if (player == null || book == null)
/* 39 */       return;  if (openNms(player, book))
/*    */       return; 
/* 41 */     ItemStack previous = player.getItemInHand();
/* 42 */     player.setItemInHand(book);
/* 43 */     player.sendMessage(ChatColor.GOLD + "Right-click the book to continue.");
/*    */ 
/*    */     
/* 46 */     if (previous != null && previous.getType() != Material.AIR) {
/* 47 */       player.getInventory().addItem(new ItemStack[] { previous });
/*    */     }
/*    */   }
/*    */   
/*    */   private static boolean openNms(Player player, ItemStack book) {
/*    */     try {
/*    */       Object packet;
/* 54 */       Class<?> packetClass = null;
/* 55 */       String[] candidates = { "net.minecraft.server.v1_8_R3.PacketPlayOutOpenBook", "net.minecraft.server.v1_8_R2.PacketPlayOutOpenBook", "net.minecraft.server.v1_8_R1.PacketPlayOutOpenBook" };
/*    */ 
/*    */ 
/*    */ 
/*    */       
/* 60 */       for (String name : candidates) {
/*    */         
/* 62 */         try { packetClass = Class.forName(name);
/* 63 */           if (packetClass != null)
/* 64 */             break;  } catch (ClassNotFoundException classNotFoundException) {}
/*    */       } 
/*    */       
/* 67 */       if (packetClass == null) return false;
/*    */       
/* 69 */       Object handle = player.getClass().getMethod("getHandle", new Class[0]).invoke(player, new Object[0]);
/* 70 */       Object connection = handle.getClass().getField("playerConnection").get(handle);
/*    */ 
/*    */       
/* 73 */       Object hand = null;
/*    */       try {
/* 75 */         Class<?> enumHandClass = Class.forName("net.minecraft.server.v1_8_R3.EnumHand");
/* 76 */         hand = enumHandClass.getEnumConstants()[0];
/* 77 */       } catch (Exception null) {}
/*    */ 
/*    */ 
/*    */       
/* 81 */       if (hand != null) {
/* 82 */         Constructor<?> ctor = packetClass.getConstructor(new Class[] { hand.getClass() });
/* 83 */         packet = ctor.newInstance(new Object[] { hand });
/*    */       } else {
/* 85 */         packet = packetClass.getConstructor(new Class[0]).newInstance(new Object[0]);
/*    */       } 
/*    */       
/* 88 */       Method sendPacket = connection.getClass().getMethod("sendPacket", new Class[] {
/* 89 */             Class.forName("net.minecraft.server.v1_8_R3.Packet") });
/* 90 */       sendPacket.invoke(connection, new Object[] { packet });
/* 91 */       return true;
/* 92 */     } catch (Throwable ignored) {
/* 93 */       return false;
/*    */     } 
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nic\\util\BookOpener.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */