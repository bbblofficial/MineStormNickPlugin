/*    */ package com.yourname.nick.util;
/*    */ 
/*    */ import org.bukkit.ChatColor;
/*    */ import org.bukkit.entity.Player;
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class Bar
/*    */ {
/*    */   public static void send(Player player, String message) {
/* 13 */     if (player == null || !player.isOnline())
/* 14 */       return;  String coloured = ChatColor.translateAlternateColorCodes('&', (message == null) ? "" : message);
/*    */ 
/*    */     
/*    */     try {
/* 18 */       player.sendMessage(coloured);
/* 19 */     } catch (Throwable throwable) {}
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nic\\util\Bar.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */