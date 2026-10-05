package com.yourname.nick.gui;

import java.io.File;
import java.util.Collections;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Typed, defaulted reader for gui.yml. Every string that appears inside
 * the /nick setup book is resolved through this class so server owners
 * can restyle the book without recompiling.
 */
public final class GuiConfig {

    public static final class Button {
        private final String label;
        private final String command;
        private final String hover;

        public Button(String label, String command, String hover) {
            this.label = color(label);
            this.command = command == null ? "" : command;
            this.hover = hover == null ? "" : hover;
        }

        public String label()   { return label; }
        public String command() { return command; }
        public String hover()   { return hover; }
    }

    private final YamlConfiguration yaml;

    public GuiConfig(JavaPlugin plugin) {
        File f = new File(plugin.getDataFolder(), "gui.yml");
        if (!f.exists()) {
            try {
                plugin.saveResource("gui.yml", false);
            } catch (Throwable ignored) {
            }
        }
        this.yaml = YamlConfiguration.loadConfiguration(f);
    }

    public String title() {
        return color(this.yaml.getString("book.title", "Nickname Setup"));
    }

    public String author() {
        return color(this.yaml.getString("book.author", "NickSystem"));
    }

    public String get(String path) {
        return this.yaml.getString(path, "");
    }

    public List<String> list(String path) {
        List<String> l = this.yaml.getStringList(path);
        return l == null ? Collections.<String>emptyList() : l;
    }

    /** Reads {@code <path>-color}, e.g. intro-color: DARK_AQUA. */
    public ChatColor color(String path) {
        String raw = this.yaml.getString(path + "-color", "BLACK");
        try {
            return ChatColor.valueOf(raw.toUpperCase());
        } catch (Throwable t) {
            return ChatColor.BLACK;
        }
    }

    /** Reads {@code <path>-style}, e.g. intro-style: BOLD. Returns null if blank. */
    public ChatColor style(String path) {
        String raw = this.yaml.getString(path + "-style", "");
        if (raw == null || raw.isEmpty()) {
            return null;
        }
        try {
            return ChatColor.valueOf(raw.toUpperCase());
        } catch (Throwable t) {
            return null;
        }
    }

    public Button button(String key) {
        String base = "buttons." + key + ".";
        return new Button(
                this.yaml.getString(base + "label", ""),
                this.yaml.getString(base + "command", ""),
                this.yaml.getString(base + "hover", ""));
    }

    public static String color(String s) {
        return ChatColor.translateAlternateColorCodes('&', s == null ? "" : s);
    }
}
