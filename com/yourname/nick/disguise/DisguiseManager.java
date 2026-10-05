/*     */ package com.yourname.nick.disguise;
/*     */ 
/*     */ import com.yourname.nick.NickPlugin;
/*     */ import com.yourname.nick.integration.BedwarsLevelHook;
/*     */ import com.yourname.nick.model.DisguiseProfile;
/*     */ import com.yourname.nick.model.NickRecord;
/*     */ import com.yourname.nick.model.Rank;
/*     */ import com.yourname.nick.model.SkinData;
/*     */ import com.yourname.nick.packet.PacketManager;
/*     */ import com.yourname.nick.storage.StorageManager;
/*     */ import java.net.InetSocketAddress;
/*     */ import java.util.Optional;
/*     */ import java.util.UUID;
/*     */ import java.util.function.BiConsumer;
/*     */ import java.util.logging.Level;
/*     */ import org.bukkit.entity.Player;
/*     */ import org.bukkit.plugin.Plugin;
/*     */ 
/*     */ 
/*     */ 
/*     */ public final class DisguiseManager
/*     */ {
/*     */   private static final String ACTION_SET = "SET";
/*     */   private static final String ACTION_RESET = "RESET";
/*     */   private final NickPlugin plugin;
/*     */   private final DisguiseRegistry registry;
/*     */   private final PacketManager packets;
/*     */   private final StorageManager storage;
/*     */   private final WorldRules rules;
/*     */   private final BedwarsLevelHook bedwars;
/*     */   
/*     */   public DisguiseManager(NickPlugin plugin, DisguiseRegistry registry, PacketManager packets, StorageManager storage, WorldRules rules, BedwarsLevelHook bedwars) {
/*  33 */     this.plugin = plugin;
/*  34 */     this.registry = registry;
/*  35 */     this.packets = packets;
/*  36 */     this.storage = storage;
/*  37 */     this.rules = rules;
/*  38 */     this.bedwars = bedwars;
/*     */   }
/*     */   
/*     */   public Optional<DisguiseProfile> profile(UUID uuid) {
/*  42 */     return this.registry.get(uuid);
/*     */   }
/*     */   
/*     */   public void apply(Player player, String nick, Rank rank, SkinData skin) {
/*  46 */     DisguiseProfile profile = install(player, nick, rank, skin, true);
/*  47 */     record(player, profile, "SET");
/*     */   }
/*     */   
/*     */   public void restore(final Player player, NickRecord stored) {
/*  51 */     install(player, stored.nickname(), stored.rank(), stored.toSkinData(), false);
/*  52 */     this.plugin.getServer().getScheduler().runTaskLater((Plugin)this.plugin, new Runnable() {
/*     */           public void run() {
/*  54 */             if (player.isOnline() && DisguiseManager.this.registry.active(player.getUniqueId()) != null) {
/*  55 */               DisguiseManager.this.refresh(player);
/*     */             }
/*     */           }
/*     */         },  2L);
/*     */   }
/*     */   
/*     */   public boolean restorePending(Player player) {
/*  62 */     Optional<NickRecord> stored = this.registry.takePending(player.getUniqueId());
/*  63 */     if (stored.isPresent()) {
/*  64 */       restore(player, stored.get());
/*  65 */       return true;
/*     */     } 
/*  67 */     return false;
/*     */   }
/*     */   
/*     */   public boolean reset(Player player) {
/*  71 */     DisguiseProfile removed = this.registry.remove(player.getUniqueId());
/*  72 */     if (removed == null) return false; 
/*  73 */     player.setDisplayName(removed.originalDisplayName());
/*  74 */     if (removed.active()) refresh(player); 
/*  75 */     record(player, removed, "RESET");
/*  76 */     return true;
/*     */   }
/*     */   
/*     */   public boolean changeSkin(Player player, SkinData skin) {
/*  80 */     Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
/*  81 */     if (!existing.isPresent()) return false; 
/*  82 */     DisguiseProfile updated = ((DisguiseProfile)existing.get()).withSkin(skin);
/*  83 */     this.registry.put(updated);
/*  84 */     if (updated.active()) refresh(player); 
/*  85 */     record(player, updated, "SET");
/*  86 */     return true;
/*     */   }
/*     */   
/*     */   public void onWorldChange(Player player) {
/*  90 */     Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
/*  91 */     if (!existing.isPresent())
/*  92 */       return;  DisguiseProfile current = existing.get();
/*  93 */     boolean shouldBeActive = this.rules.isActive(player.getWorld().getName());
/*  94 */     if (shouldBeActive == current.active())
/*  95 */       return;  DisguiseProfile updated = current.withActive(shouldBeActive);
/*  96 */     this.registry.put(updated);
/*  97 */     player.setDisplayName(shouldBeActive ? updated.styledName() : updated.originalDisplayName());
/*  98 */     refresh(player);
/*     */   }
/*     */   
/*     */   public void unload(Player player) {
/* 102 */     this.registry.remove(player.getUniqueId());
/*     */   }
/*     */   
/*     */   public void shutdown() {
/* 106 */     for (DisguiseProfile profile : this.registry.all()) {
/* 107 */       Player player = this.plugin.getServer().getPlayer(profile.realUuid());
/* 108 */       if (player != null) {
/* 109 */         player.setDisplayName(profile.originalDisplayName());
/*     */       }
/*     */     } 
/* 112 */     this.registry.clear();
/*     */   }
/*     */   
/*     */   private DisguiseProfile install(Player player, String nick, Rank rank, SkinData skin, boolean refreshNow) {
/* 116 */     Optional<DisguiseProfile> previous = this.registry.get(player.getUniqueId());
/*     */ 
/*     */     
/* 119 */     String original = previous.isPresent() ? ((DisguiseProfile)previous.get()).originalDisplayName() : player.getDisplayName();
/* 120 */     boolean active = this.rules.isActive(player.getWorld().getName());
/*     */     
/* 122 */     DisguiseProfile profile = new DisguiseProfile(player.getUniqueId(), player.getName(), nick, rank, skin, this.bedwars.rollStars(), active, original);
/* 123 */     this.registry.put(profile);
/* 124 */     player.setDisplayName(active ? profile.styledName() : original);
/*     */     
/* 126 */     boolean wasActive = (previous.isPresent() && ((DisguiseProfile)previous.get()).active());
/* 127 */     if (refreshNow && (active || wasActive)) refresh(player); 
/* 128 */     return profile;
/*     */   }
/*     */ 
/*     */   
/*     */   private void refresh(Player target) {
/* 133 */     for (Player viewer : this.plugin.getServer().getOnlinePlayers()) {
/* 134 */       if (viewer.equals(target) || !viewer.canSee(target))
/* 135 */         continue;  viewer.hidePlayer(target);
/* 136 */       viewer.showPlayer(target);
/*     */     } 
/* 138 */     this.packets.resendOwnEntry(target);
/*     */   }
/*     */   
/*     */   private void record(Player player, DisguiseProfile profile, String action) {
/* 142 */     InetSocketAddress address = player.getAddress();
/*     */     
/* 144 */     String ip = (address == null || address.getAddress() == null) ? "unknown" : address.getAddress().getHostAddress();
/*     */ 
/*     */     
/* 147 */     NickRecord row = new NickRecord(profile.realUuid(), profile.realName(), profile.nickname(), profile.rank().name(), profile.skin().sourceKey(), profile.skin().value(), profile.skin().signature(), action, System.currentTimeMillis(), ip);
/* 148 */     this.storage.insert(row).whenComplete(new BiConsumer<Void, Throwable>() {
/*     */           public void accept(Void ignored, Throwable error) {
/* 150 */             if (error != null)
/* 151 */               DisguiseManager.this.plugin.getLogger().log(Level.SEVERE, "Failed to persist nick action", error); 
/*     */           }
/*     */         });
/*     */   }
/*     */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\disguise\DisguiseManager.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */