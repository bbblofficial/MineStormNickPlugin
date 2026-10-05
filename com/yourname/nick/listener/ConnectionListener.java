/*    */ package com.yourname.nick.listener;
/*    */ 
/*    */ import com.yourname.nick.NickPlugin;
/*    */ import com.yourname.nick.disguise.DisguiseManager;
/*    */ import com.yourname.nick.disguise.DisguiseRegistry;
/*    */ import com.yourname.nick.gui.BookGUIManager;
/*    */ import com.yourname.nick.model.DisguiseProfile;
/*    */ import com.yourname.nick.model.NickRecord;
/*    */ import com.yourname.nick.storage.StorageManager;
/*    */ import com.yourname.nick.util.NameMasker;
/*    */ import java.util.Collections;
/*    */ import java.util.Optional;
/*    */ import java.util.concurrent.ExecutionException;
/*    */ import java.util.concurrent.TimeUnit;
/*    */ import org.bukkit.event.EventHandler;
/*    */ import org.bukkit.event.EventPriority;
/*    */ import org.bukkit.event.Listener;
/*    */ import org.bukkit.event.player.AsyncPlayerPreLoginEvent;
/*    */ import org.bukkit.event.player.PlayerJoinEvent;
/*    */ import org.bukkit.event.player.PlayerQuitEvent;
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class ConnectionListener
/*    */   implements Listener
/*    */ {
/*    */   private final NickPlugin plugin;
/*    */   private final DisguiseRegistry registry;
/*    */   private final DisguiseManager disguises;
/*    */   private final StorageManager storage;
/*    */   private final BookGUIManager bookGui;
/*    */   private final boolean persist;
/*    */   private final boolean maskMessages;
/*    */   
/*    */   public ConnectionListener(NickPlugin plugin, DisguiseRegistry registry, DisguiseManager disguises, StorageManager storage, BookGUIManager bookGui) {
/* 36 */     this.plugin = plugin;
/* 37 */     this.registry = registry;
/* 38 */     this.disguises = disguises;
/* 39 */     this.storage = storage;
/* 40 */     this.bookGui = bookGui;
/* 41 */     this.persist = plugin.getConfig().getBoolean("settings.persist-across-sessions", true);
/* 42 */     this.maskMessages = plugin.getConfig().getBoolean("settings.rewrite-join-quit", true);
/*    */   }
/*    */   
/*    */   @EventHandler
/*    */   public void onPreLogin(AsyncPlayerPreLoginEvent event) {
/* 47 */     if (!this.persist)
/*    */       return;  try {
/* 49 */       Optional<NickRecord> latest = this.storage.findLatestForPlayer(event.getUniqueId()).get(5L, TimeUnit.SECONDS);
/* 50 */       if (latest.isPresent() && "SET".equals(((NickRecord)latest.get()).action())) {
/* 51 */         this.registry.stagePending(event.getUniqueId(), latest.get());
/*    */       }
/* 53 */     } catch (InterruptedException e) {
/* 54 */       Thread.currentThread().interrupt();
/* 55 */     } catch (ExecutionException|java.util.concurrent.TimeoutException e) {
/* 56 */       this.plugin.getLogger().warning("Could not load nick state for " + event.getName() + ": " + e.getMessage());
/*    */     } 
/*    */   }
/*    */   
/*    */   @EventHandler(priority = EventPriority.LOWEST)
/*    */   public void onJoin(PlayerJoinEvent event) {
/* 62 */     this.disguises.restorePending(event.getPlayer());
/*    */   }
/*    */   
/*    */   @EventHandler(priority = EventPriority.HIGH)
/*    */   public void onJoinMessage(PlayerJoinEvent event) {
/* 67 */     if (!this.maskMessages)
/* 68 */       return;  DisguiseProfile profile = this.registry.active(event.getPlayer().getUniqueId());
/* 69 */     String message = event.getJoinMessage();
/* 70 */     if (profile != null && message != null) {
/* 71 */       event.setJoinMessage(NameMasker.mask(message, Collections.singletonList(profile)));
/*    */     }
/*    */   }
/*    */   
/*    */   @EventHandler(priority = EventPriority.HIGH)
/*    */   public void onQuitMessage(PlayerQuitEvent event) {
/* 77 */     if (!this.maskMessages)
/* 78 */       return;  DisguiseProfile profile = this.registry.active(event.getPlayer().getUniqueId());
/* 79 */     String message = event.getQuitMessage();
/* 80 */     if (profile != null && message != null) {
/* 81 */       event.setQuitMessage(NameMasker.mask(message, Collections.singletonList(profile)));
/*    */     }
/*    */   }
/*    */   
/*    */   @EventHandler(priority = EventPriority.MONITOR)
/*    */   public void onQuit(PlayerQuitEvent event) {
/* 87 */     this.disguises.unload(event.getPlayer());
/* 88 */     this.bookGui.clearSession(event.getPlayer().getUniqueId());
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\listener\ConnectionListener.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */