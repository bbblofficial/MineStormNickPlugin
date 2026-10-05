package com.yourname.nick.disguise;

import com.yourname.nick.model.DisguiseProfile;
import com.yourname.nick.model.NickRecord;
import java.util.ArrayList;
import java.util.Collection;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Optional;
import java.util.UUID;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.ConcurrentMap;




public final class DisguiseRegistry
{
  private static final class Pending
  {
    final NickRecord record;
    final long stagedAt;
    
    Pending(NickRecord record, long stagedAt) {
      this.record = record;
      this.stagedAt = stagedAt;
    }
    NickRecord record() { return this.record; } long stagedAt() {
      return this.stagedAt;
    }
  }
  private final ConcurrentMap<UUID, DisguiseProfile> profiles = new ConcurrentHashMap<>();
  private final ConcurrentMap<String, UUID> nickIndex = new ConcurrentHashMap<>();
  private final ConcurrentMap<UUID, Pending> pending = new ConcurrentHashMap<>();
  public boolean isEmpty() {
    return this.profiles.isEmpty();
  }
  public Optional<DisguiseProfile> get(UUID uuid) {
    return Optional.ofNullable(this.profiles.get(uuid));
  }

  
  public DisguiseProfile active(UUID uuid) {
    DisguiseProfile profile = this.profiles.get(uuid);
    return (profile != null && profile.active()) ? profile : null;
  }
  
  public void put(DisguiseProfile profile) {
    DisguiseProfile previous = this.profiles.put(profile.realUuid(), profile);
    if (previous != null && !previous.nickname().equalsIgnoreCase(profile.nickname())) {
      this.nickIndex.remove(key(previous.nickname()), previous.realUuid());
    }
    this.nickIndex.put(key(profile.nickname()), profile.realUuid());
  }
  
  public DisguiseProfile remove(UUID uuid) {
    DisguiseProfile previous = this.profiles.remove(uuid);
    if (previous != null) this.nickIndex.remove(key(previous.nickname()), uuid); 
    return previous;
  }
  
  public boolean isNickInUse(String nick, UUID except) {
    UUID owner = this.nickIndex.get(key(nick));
    return (owner != null && !owner.equals(except));
  }
  
  public Optional<DisguiseProfile> findByNick(String nick) {
    UUID owner = this.nickIndex.get(key(nick));
    return (owner == null) ? Optional.<DisguiseProfile>empty() : get(owner);
  }
  
  public Collection<DisguiseProfile> all() {
    return new ArrayList<>(this.profiles.values());
  }
  
  public void stagePending(UUID uuid, NickRecord record) {
    this.pending.put(uuid, new Pending(record, System.currentTimeMillis()));
  }
  
  public Optional<NickRecord> takePending(UUID uuid) {
    Pending taken = this.pending.remove(uuid);
    return (taken == null) ? Optional.<NickRecord>empty() : Optional.<NickRecord>of(taken.record());
  }
  
  public void prunePending(long maxAgeMillis) {
    long cutoff = System.currentTimeMillis() - maxAgeMillis;
    List<UUID> toRemove = new ArrayList<>();
    for (Map.Entry<UUID, Pending> entry : this.pending.entrySet()) {
      if (((Pending)entry.getValue()).stagedAt() < cutoff) toRemove.add(entry.getKey()); 
    } 
    for (UUID uuid : toRemove) this.pending.remove(uuid); 
  }
  
  public void clear() {
    this.profiles.clear();
    this.nickIndex.clear();
    this.pending.clear();
  }
  
  private static String key(String nick) {
    return nick.toLowerCase(Locale.ROOT);
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\disguise\DisguiseRegistry.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */