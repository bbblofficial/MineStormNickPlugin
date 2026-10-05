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

public final class DisguiseManager {

    private static final String ACTION_SET   = "SET";
    private static final String ACTION_RESET = "RESET";

    private final NickPlugin plugin;
    private final DisguiseRegistry registry;
    private final PacketManager packets;
    private final StorageManager storage;
    private final WorldRules rules;
    private final BedwarsLevelHook bedwars;

    public DisguiseManager(NickPlugin plugin,
                           DisguiseRegistry registry,
                           PacketManager packets,
                           StorageManager storage,
                           WorldRules rules,
                           BedwarsLevelHook bedwars) {
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
        record(player, profile, ACTION_SET);
    }

    public void restore(final Player player, NickRecord stored) {
        install(player, stored.nickname(), stored.rank(), stored.toSkinData(), false);
        this.plugin.getServer().getScheduler().runTaskLater(this.plugin,
                new Runnable() {
                    @Override
                    public void run() {
                        if (player.isOnline()
                                && DisguiseManager.this.registry.active(
                                        player.getUniqueId()) != null) {
                            DisguiseManager.this.refresh(player);
                        }
                    }
                }, 2L);
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
        if (removed == null) {
            return false;
        }
        player.setDisplayName(removed.originalDisplayName());
        refresh(player);
        record(player, removed, ACTION_RESET);
        return true;
    }

    public boolean changeSkin(Player player, SkinData skin) {
        Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
        if (!existing.isPresent()) {
            return false;
        }
        DisguiseProfile updated = existing.get().withSkin(skin);
        this.registry.put(updated);
        refresh(player);
        record(player, updated, ACTION_SET);
        return true;
    }

    public void onWorldChange(Player player) {
        Optional<DisguiseProfile> existing = this.registry.get(player.getUniqueId());
        if (!existing.isPresent()) {
            return;
        }
        DisguiseProfile current = existing.get();
        boolean shouldBeActive = this.rules.isActive(player.getWorld().getName());
        if (shouldBeActive == current.active()) {
            return;
        }
        DisguiseProfile updated = current.withActive(shouldBeActive);
        this.registry.put(updated);
        player.setDisplayName(shouldBeActive
                ? updated.styledName()
                : updated.originalDisplayName());
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

    /* ------------------------------------------------------------------ */
    /*  Internals                                                         */
    /* ------------------------------------------------------------------ */

    private DisguiseProfile install(Player player,
                                    String nick,
                                    Rank rank,
                                    SkinData skin,
                                    boolean refreshNow) {
        Optional<DisguiseProfile> previous = this.registry.get(player.getUniqueId());

        String original = previous.isPresent()
                ? previous.get().originalDisplayName()
                : player.getDisplayName();
        boolean active = this.rules.isActive(player.getWorld().getName());

        DisguiseProfile profile = new DisguiseProfile(
                player.getUniqueId(),
                player.getName(),
                nick,
                rank,
                skin,
                this.bedwars.rollStars(),
                active,
                original);

        this.registry.put(profile);
        player.setDisplayName(active ? profile.styledName() : original);

        if (refreshNow) {
            refresh(player);
        }
        return profile;
    }

    private void refresh(final Player target) {
        if (target == null || !target.isOnline()) {
            return;
        }
        // Defer by one tick so the plugin has time to settle and the
        // tab-list entry exists before we overwrite it.
        this.plugin.getServer().getScheduler().runTaskLater(this.plugin,
                new Runnable() {
                    @Override
                    public void run() {
                        if (!target.isOnline()) {
                            return;
                        }
                        packets.resendOwnEntry(target);
                    }
                }, 1L);
    }

    private void record(Player player, DisguiseProfile profile, String action) {
        InetSocketAddress address = player.getAddress();
        String ip = (address == null || address.getAddress() == null)
                ? "unknown"
                : address.getAddress().getHostAddress();

        NickRecord row = new NickRecord(
                profile.realUuid(),
                profile.realName(),
                profile.nickname(),
                profile.rank().name(),
                profile.skin().sourceKey(),
                profile.skin().value(),
                profile.skin().signature(),
                action,
                System.currentTimeMillis(),
                ip);

        this.storage.insert(row).whenComplete(new BiConsumer<Void, Throwable>() {
            @Override
            public void accept(Void ignored, Throwable error) {
                if (error != null) {
                    plugin.getLogger().log(Level.SEVERE,
                            "Failed to persist nick action", error);
                }
            }
        });
    }
}
