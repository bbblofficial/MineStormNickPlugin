package com.yourname.nick;

import com.yourname.nick.command.NickCommand;
import com.yourname.nick.command.RealNameCommand;
import com.yourname.nick.disguise.DisguiseManager;
import com.yourname.nick.disguise.DisguiseRegistry;
import com.yourname.nick.disguise.WorldRules;
import com.yourname.nick.gui.BookGUIManager;
import com.yourname.nick.integration.BedwarsLevelHook;
import com.yourname.nick.integration.NickPlaceholderExpansion;
import com.yourname.nick.listener.ChatListener;
import com.yourname.nick.listener.ConnectionListener;
import com.yourname.nick.listener.WorldListener;
import com.yourname.nick.message.Messages;
import com.yourname.nick.name.NameGenerator;
import com.yourname.nick.name.NameValidator;
import com.yourname.nick.packet.PacketManager;
import com.yourname.nick.skin.SkinCacheManager;
import com.yourname.nick.storage.StorageManager;
import com.yourname.nick.task.ActionBarTask;
import com.yourname.nick.util.Async;
import java.io.File;
import java.util.logging.Level;
import org.bukkit.command.PluginCommand;
import org.bukkit.command.TabExecutor;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.Plugin;
import org.bukkit.plugin.PluginManager;
import org.bukkit.plugin.java.JavaPlugin;

public final class NickPlugin extends JavaPlugin {

    private DisguiseRegistry registry;
    private PacketManager    packets;
    private StorageManager   storage;
    private SkinCacheManager skins;
    private DisguiseManager  disguises;
    private BookGUIManager   bookGui;
    private Runnable         placeholderCleanup;

    @Override
    public void onLoad() {
        this.registry = new DisguiseRegistry();
        this.packets  = new PacketManager(this, this.registry);
        this.packets.load();
    }

    @Override
    public void onEnable() {
        saveDefaultConfig();
        YamlConfiguration names = loadNames();
        Messages messages = new Messages(this);

        if (!this.packets.enable()) {
            getLogger().severe(
                    "NickSystem requires Paper 1.19.3 or newer (player info update packets). Disabling.");
            getServer().getPluginManager().disablePlugin(this);
            return;
        }

        this.storage = new StorageManager(this);
        this.storage.initialize().whenComplete((ignored, error) -> {
            if (error != null) {
                getLogger().log(Level.SEVERE,
                        "Database initialisation failed; disabling NickSystem.", error);
                Async.main(NickPlugin.this, new Runnable() {
                    @Override
                    public void run() {
                        getServer().getPluginManager().disablePlugin(NickPlugin.this);
                    }
                });
            }
        });

        this.skins = new SkinCacheManager(this);
        this.skins.initialize();

        NameValidator validator = new NameValidator(names, this.registry);
        NameGenerator generator = new NameGenerator(names, validator);
        BedwarsLevelHook bedwars = new BedwarsLevelHook(getConfig());
        WorldRules rules = WorldRules.fromConfig(getConfig(), getLogger());

        this.disguises = new DisguiseManager(
                this, this.registry, this.packets, this.storage, rules, bedwars);
        this.bookGui = new BookGUIManager(
                this, messages, this.disguises, this.skins, generator, validator, this.storage);

        PluginManager pluginManager = getServer().getPluginManager();
        pluginManager.registerEvents(new ConnectionListener(
                this, this.registry, this.disguises, this.storage, this.bookGui), this);
        pluginManager.registerEvents(new WorldListener(this.disguises), this);
        pluginManager.registerEvents(new ChatListener(getConfig(), this.registry, bedwars), this);

        bind("nick", new NickCommand(this, messages, this.bookGui, this.disguises, this.skins, validator));
        bind("realname", new RealNameCommand(this, messages, this.registry, this.storage));

        if (getConfig().getBoolean("actionbar.enabled", true)) {
            long interval = Math.max(10L, getConfig().getLong("actionbar.interval-ticks", 40L));
            ActionBarTask task = new ActionBarTask(
                    this, this.registry,
                    messages.get("actionbar"),
                    getConfig().getBoolean("actionbar.show-when-dormant", true));
            getServer().getScheduler().runTaskTimer(this, task, interval, interval);
        }
        getServer().getScheduler().runTaskTimerAsynchronously(
                this, new Runnable() {
                    @Override
                    public void run() {
                        registry.prunePending(60000L);
                    }
                }, 1200L, 1200L);

        if (pluginManager.isPluginEnabled("PlaceholderAPI")) {
            final NickPlaceholderExpansion expansion =
                    new NickPlaceholderExpansion(this, this.registry, bedwars);
            expansion.register();
            this.placeholderCleanup = new Runnable() {
                @Override
                public void run() {
                    expansion.unregister();
                }
            };
        }
    }

    @Override
    public void onDisable() {
        getServer().getScheduler().cancelTasks(this);
        if (this.placeholderCleanup != null) {
            this.placeholderCleanup.run();
            this.placeholderCleanup = null;
        }
        if (this.disguises != null) this.disguises.shutdown();
        if (this.bookGui   != null) this.bookGui.clear();
        if (this.skins     != null) this.skins.shutdown();
        if (this.storage   != null) this.storage.close();
        if (this.packets   != null) this.packets.disable();
    }

    private YamlConfiguration loadNames() {
        File file = new File(getDataFolder(), "names.yml");
        if (!file.exists()) {
            saveResource("names.yml", false);
        }
        return YamlConfiguration.loadConfiguration(file);
    }

    private void bind(String name, TabExecutor executor) {
        PluginCommand command = getCommand(name);
        if (command == null) {
            throw new IllegalStateException("Command '" + name + "' is missing from plugin.yml");
        }
        command.setExecutor(executor);
        command.setTabCompleter(executor);
    }
}
