/*    */ package com.yourname.nick.packet;
/*    */ 
/*    */ import com.yourname.nick.NickPlugin;
/*    */ import com.yourname.nick.disguise.DisguiseRegistry;
/*    */ import org.bukkit.entity.Player;
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class PacketManager
/*    */ {
/*    */   private final NickPlugin plugin;
/*    */   private final DisguiseRegistry registry;
/*    */   
/*    */   public PacketManager(NickPlugin plugin, DisguiseRegistry registry) {
/* 22 */     this.plugin = plugin;
/* 23 */     this.registry = registry;
/*    */   }
/*    */ 
/*    */   
/*    */   public boolean enable() {
/* 28 */     return true;
/*    */   }
/*    */   public void load() {}
/*    */   
/*    */   public void disable() {}
/*    */   
/*    */   public void resendOwnEntry(Player player) {
/* 35 */     if (player != null && player.isOnline())
/* 36 */       player.setDisplayName(player.getDisplayName()); 
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\packet\PacketManager.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */