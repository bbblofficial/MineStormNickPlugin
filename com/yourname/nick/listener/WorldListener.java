/*    */ package com.yourname.nick.listener;
/*    */ 
/*    */ import com.yourname.nick.disguise.DisguiseManager;
/*    */ import org.bukkit.event.EventHandler;
/*    */ import org.bukkit.event.EventPriority;
/*    */ import org.bukkit.event.Listener;
/*    */ import org.bukkit.event.player.PlayerChangedWorldEvent;
/*    */ 
/*    */ public final class WorldListener
/*    */   implements Listener {
/*    */   private final DisguiseManager disguises;
/*    */   
/*    */   public WorldListener(DisguiseManager disguises) {
/* 14 */     this.disguises = disguises;
/*    */   }
/*    */   
/*    */   @EventHandler(priority = EventPriority.MONITOR)
/*    */   public void onWorldChange(PlayerChangedWorldEvent event) {
/* 19 */     this.disguises.onWorldChange(event.getPlayer());
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\listener\WorldListener.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */