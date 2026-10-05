package com.yourname.nick.disguise;

import com.yourname.nick.NickPlugin;
import com.yourname.nick.integration.BedwarsLevelHook;
import com.yourname.nick.model.DisguiseProfile;
import com.yourname.nick.model.NickRecord;
import com.yourname.nick.model.Rank;
import com.yourname.nick.model.SkinData;
import com.yourname.nick.packet.PacketManager;
import com.yourname.nick.storage.StorageManager;
import java.net.InetSocketAddress;
import java.util.Optional;
import java.util.UUID;
import java.util.function.BiConsumer;
import java.util.logging.Level;
import org.bukkit.entity.Player;
import org.bukkit.plugin.Plugin;



public final class DisguiseManager
{
  private static final String ACTION_SET = "SET";
  private static final String ACTION_RESET = "RESET";
  private final NickPlugin plugin;
  private final DisguiseRegistry registry;
  private final PacketManager packets;
  private final StorageManager storage;
  private final WorldRules rules;
  private final BedwarsLevelHook bedwars;
  
  public DisguiseManager(NickPlugin plugin, DisguiseRegistry registry, PacketManager packets, StorageManager storage, WorldRules rules, BedwarsLevelHook bedwars) {
    this.plugin = plugin;
    this.registry = registry;
    this.packets = packets;
    this.storage = storage;
    this.rules = rules;
    this.bedwars = bedwars;
  }
  
  public Optional<DisguiseProfile> profile(UUID uuid) {
    return this.registry.get(uuid);
  }
  
  public void apply(Player player, String nick, Rank rank, SkinData skin) {
    DisguiseProfile profile = install(player, nick, rank, skin, true);
    record(player, profile, "SET");
  }
  
  public void restore(final Player player, NickRecord stored) {
    install(player, stored.nickname(), stored.rank(), stored.toSkinData(), false);
    this.plugin.getServer().getScheduler().runTaskLater((Plugin)this.plugin, new Runnable() {
          public void run() {
            if (player.isOnline() && DisguiseManager.this.registry.active(player.getUniqueId()) != null) {
              DisguiseManager.this.refresh(player);
            }
          }
        },  2L);
  }
  
  public boolean restorePending(Player player) {
    Optional<NickRecord> stored = this.registry.takePending(player.getUniqueId());
    if (stored.isPresent()) {
      restore(player, stored.get());
      return true;
    } 
    return false;
  }
  
  public boolean reset(Player player) {
    DisguiseProfile removed = this.registry.remove(player.getUniqueId());
    if (removed == null) return false; 
    player.setDisplayName(removed.originalDisplayName());
    if (removed.active()) refresh(player); 
    record(player, removed, "RESET");
    return true;
  }
  
  public boolean changeSkin(Player player, SkinData skin) {
    Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
    if (!existing.isPresent()) return false; 
    DisguiseProfile updated = ((DisguiseProfile)existing.get()).withSkin(skin);
    this.registry.put(updated);
    if (updated.active()) refresh(player); 
    record(player, updated, "SET");
    return true;
  }
  
  public void onWorldChange(Player player) {
    Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
    if (!existing.isPresent())
      return;  DisguiseProfile current = existing.get();
    boolean shouldBeActive = this.rules.isActive(player.getWorld().getName());
    if (shouldBeActive == current.active())
      return;  DisguiseProfile updated = current.withActive(shouldBeActive);
    this.registry.put(updated);
    player.setDisplayName(shouldBeActive ? updated.styledName() : updated.originalDisplayName());
    refresh(player);
  }
  
  public void unload(Player player) {
    this.registry.remove(player.getUniqueId());
  }
  
  public void shutdown() {
    for (DisguiseProfile profile : this.registry.all()) {
      Player player = this.plugin.getServer().getPlayer(profile.realUuid());
      if (player != null) {
        player.setDisplayName(profile.originalDisplayName());
      }
    } 
    this.registry.clear();
  }
  
  private DisguiseProfile install(Player player, String nick, Rank rank, SkinData skin, boolean refreshNow) {
    Optional<DisguiseProfile> previous = this.registry.get(player.getUniqueId());

    
    String original = previous.isPresent() ? ((DisguiseProfile)previous.get()).originalDisplayName() : player.getDisplayName();
    boolean active = this.rules.isActive(player.getWorld().getName());
    
    DisguiseProfile profile = new DisguiseProfile(player.getUniqueId(), player.getName(), nick, rank, skin, this.bedwars.rollStars(), active, original);
    this.registry.put(profile);
    player.setDisplayName(active ? profile.styledName() : original);
    
    boolean wasActive = (previous.isPresent() && ((DisguiseProfile)previous.get()).active());
    if (refreshNow && (active || wasActive)) refresh(player); 
    return profile;
  }

  
  private void refresh(Player target) {
    for (Player viewer : this.plugin.getServer().getOnlinePlayers()) {
      if (viewer.equals(target) || !viewer.canSee(target))
        continue;  viewer.hidePlayer(target);
      viewer.showPlayer(target);
    } 
    this.packets.resendOwnEntry(target);
  }
  
  private void record(Player player, DisguiseProfile profile, String action) {
    InetSocketAddress address = player.getAddress();
    
    String ip = (address == null || address.getAddress() == null) ? "unknown" : address.getAddress().getHostAddress();

    
    NickRecord row = new NickRecord(profile.realUuid(), profile.realName(), profile.nickname(), profile.rank().name(), profile.skin().sourceKey(), profile.skin().value(), profile.skin().signature(), action, System.currentTimeMillis(), ip);
    this.storage.insert(row).whenComplete(new BiConsumer<Void, Throwable>() {
          public void accept(Void ignored, Throwable error) {
            if (error != null)
              DisguiseManager.this.plugin.getLogger().log(Level.SEVERE, "Failed to persist nick action", error); 
          }
        });
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\disguise\DisguiseManager.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */