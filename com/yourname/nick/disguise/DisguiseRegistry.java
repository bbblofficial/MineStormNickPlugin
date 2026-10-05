/*     */ package com.yourname.nick.disguise;
/*     */ 
/*     */ import com.yourname.nick.model.DisguiseProfile;
/*     */ import com.yourname.nick.model.NickRecord;
/*     */ import java.util.ArrayList;
/*     */ import java.util.Collection;
/*     */ import java.util.List;
/*     */ import java.util.Locale;
/*     */ import java.util.Map;
/*     */ import java.util.Optional;
/*     */ import java.util.UUID;
/*     */ import java.util.concurrent.ConcurrentHashMap;
/*     */ import java.util.concurrent.ConcurrentMap;
/*     */ 
/*     */ 
/*     */ 
/*     */ 
/*     */ public final class DisguiseRegistry
/*     */ {
/*     */   private static final class Pending
/*     */   {
/*     */     final NickRecord record;
/*     */     final long stagedAt;
/*     */     
/*     */     Pending(NickRecord record, long stagedAt) {
/*  26 */       this.record = record;
/*  27 */       this.stagedAt = stagedAt;
/*     */     }
/*  29 */     NickRecord record() { return this.record; } long stagedAt() {
/*  30 */       return this.stagedAt;
/*     */     }
/*     */   }
/*  33 */   private final ConcurrentMap<UUID, DisguiseProfile> profiles = new ConcurrentHashMap<>();
/*  34 */   private final ConcurrentMap<String, UUID> nickIndex = new ConcurrentHashMap<>();
/*  35 */   private final ConcurrentMap<UUID, Pending> pending = new ConcurrentHashMap<>();
/*     */   public boolean isEmpty() {
/*  37 */     return this.profiles.isEmpty();
/*     */   }
/*     */   public Optional<DisguiseProfile> get(UUID uuid) {
/*  40 */     return Optional.ofNullable(this.profiles.get(uuid));
/*     */   }
/*     */ 
/*     */   
/*     */   public DisguiseProfile active(UUID uuid) {
/*  45 */     DisguiseProfile profile = this.profiles.get(uuid);
/*  46 */     return (profile != null && profile.active()) ? profile : null;
/*     */   }
/*     */   
/*     */   public void put(DisguiseProfile profile) {
/*  50 */     DisguiseProfile previous = this.profiles.put(profile.realUuid(), profile);
/*  51 */     if (previous != null && !previous.nickname().equalsIgnoreCase(profile.nickname())) {
/*  52 */       this.nickIndex.remove(key(previous.nickname()), previous.realUuid());
/*     */     }
/*  54 */     this.nickIndex.put(key(profile.nickname()), profile.realUuid());
/*     */   }
/*     */   
/*     */   public DisguiseProfile remove(UUID uuid) {
/*  58 */     DisguiseProfile previous = this.profiles.remove(uuid);
/*  59 */     if (previous != null) this.nickIndex.remove(key(previous.nickname()), uuid); 
/*  60 */     return previous;
/*     */   }
/*     */   
/*     */   public boolean isNickInUse(String nick, UUID except) {
/*  64 */     UUID owner = this.nickIndex.get(key(nick));
/*  65 */     return (owner != null && !owner.equals(except));
/*     */   }
/*     */   
/*     */   public Optional<DisguiseProfile> findByNick(String nick) {
/*  69 */     UUID owner = this.nickIndex.get(key(nick));
/*  70 */     return (owner == null) ? Optional.<DisguiseProfile>empty() : get(owner);
/*     */   }
/*     */   
/*     */   public Collection<DisguiseProfile> all() {
/*  74 */     return new ArrayList<>(this.profiles.values());
/*     */   }
/*     */   
/*     */   public void stagePending(UUID uuid, NickRecord record) {
/*  78 */     this.pending.put(uuid, new Pending(record, System.currentTimeMillis()));
/*     */   }
/*     */   
/*     */   public Optional<NickRecord> takePending(UUID uuid) {
/*  82 */     Pending taken = this.pending.remove(uuid);
/*  83 */     return (taken == null) ? Optional.<NickRecord>empty() : Optional.<NickRecord>of(taken.record());
/*     */   }
/*     */   
/*     */   public void prunePending(long maxAgeMillis) {
/*  87 */     long cutoff = System.currentTimeMillis() - maxAgeMillis;
/*  88 */     List<UUID> toRemove = new ArrayList<>();
/*  89 */     for (Map.Entry<UUID, Pending> entry : this.pending.entrySet()) {
/*  90 */       if (((Pending)entry.getValue()).stagedAt() < cutoff) toRemove.add(entry.getKey()); 
/*     */     } 
/*  92 */     for (UUID uuid : toRemove) this.pending.remove(uuid); 
/*     */   }
/*     */   
/*     */   public void clear() {
/*  96 */     this.profiles.clear();
/*  97 */     this.nickIndex.clear();
/*  98 */     this.pending.clear();
/*     */   }
/*     */   
/*     */   private static String key(String nick) {
/* 102 */     return nick.toLowerCase(Locale.ROOT);
/*     */   }
/*     */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\disguise\DisguiseRegistry.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */