/*    */ package com.yourname.nick.listener;
/*    */ 
/*    */ import com.yourname.nick.disguise.DisguiseRegistry;
/*    */ import com.yourname.nick.integration.BedwarsLevelHook;
/*    */ import com.yourname.nick.model.DisguiseProfile;
/*    */ import com.yourname.nick.util.NameMasker;
/*    */ import org.bukkit.ChatColor;
/*    */ import org.bukkit.configuration.ConfigurationSection;
/*    */ import org.bukkit.event.EventHandler;
/*    */ import org.bukkit.event.EventPriority;
/*    */ import org.bukkit.event.Listener;
/*    */ import org.bukkit.event.entity.PlayerDeathEvent;
/*    */ import org.bukkit.event.player.AsyncPlayerChatEvent;
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class ChatListener
/*    */   implements Listener
/*    */ {
/*    */   private final DisguiseRegistry registry;
/*    */   private final BedwarsLevelHook bedwars;
/*    */   private final boolean rewriteChat;
/*    */   
/*    */   public ChatListener(ConfigurationSection config, DisguiseRegistry registry, BedwarsLevelHook bedwars) {
/* 28 */     this.registry = registry;
/* 29 */     this.bedwars = bedwars;
/* 30 */     this.rewriteChat = config.getBoolean("settings.rewrite-chat", true);
/*    */   }
/*    */   
/*    */   @EventHandler(priority = EventPriority.HIGH, ignoreCancelled = true)
/*    */   public void onChat(AsyncPlayerChatEvent event) {
/* 35 */     if (!this.rewriteChat)
/* 36 */       return;  DisguiseProfile profile = this.registry.active(event.getPlayer().getUniqueId());
/* 37 */     if (profile == null)
/*    */       return; 
/* 39 */     StringBuilder format = new StringBuilder();
/* 40 */     String level = this.bedwars.chatPrefix(profile);
/* 41 */     if (level != null) format.append(level); 
/* 42 */     format.append(profile.styledName());
/* 43 */     format.append(ChatColor.RESET).append(": ").append(ChatColor.WHITE).append("%2$s");
/* 44 */     event.setFormat(format.toString());
/*    */   }
/*    */   
/*    */   @EventHandler(priority = EventPriority.HIGH)
/*    */   public void onDeath(PlayerDeathEvent event) {
/* 49 */     String message = event.getDeathMessage();
/* 50 */     if (message != null)
/* 51 */       event.setDeathMessage(NameMasker.mask(message, this.registry.all())); 
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\listener\ChatListener.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */