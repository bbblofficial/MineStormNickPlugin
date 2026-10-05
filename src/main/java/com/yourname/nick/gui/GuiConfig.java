package com.yourname.nick.gui;

import java.io.File;
import java.util.Collections;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.java.JavaPlugin;

/**
 * Typed, defaulted reader for gui.yml.
 *
 * <p>Method split (this fixes the previous ambiguous-overload compile
 * error):</p>
 * <ul>
 *   <li>{@link #colorize(String)} - <b>static</b> utility that translates
 *       '&amp;' colour codes in any string.</li>
 *   <li>{@link #color(String)} - <b>instance</b> reader that looks up
 *       {@code &lt;page&gt;-color} (e.g. {@code intro-color: DARK_AQUA})
 *       and returns a {@link ChatColor}.</li>
 *   <li>{@link #style(String)} - instance reader for {@code <page>-style}.</li>
 * </ul>
 */
public final class GuiConfig {

    public static final class Button {
        private final String label;
        private final String command;
        private final String hover;

        public Button(String label, String command, String hover) {
            this.label = colorize(label);
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
            try { plugin.saveResource("gui.yml", false); }
            catch (Throwable ignored) { }
        }
        this.yaml = YamlConfiguration.loadConfiguration(f);
    }

    /* ------------------------------------------------------------------ */
    /*  Book chrome                                                       */
    /* ------------------------------------------------------------------ */

    public String title()  { return colorize(this.yaml.getString("book.title",  "Nickname Setup")); }
    public String author() { return colorize(this.yaml.getString("book.author", "MineStormNickSystem")); }

    /* ------------------------------------------------------------------ */
    /*  Generic readers                                                   */
    /* ------------------------------------------------------------------ */

    public String get(String path) {
        return this.yaml.getString(path, "");
    }

    public List<String> list(String path) {
        List<String> l = this.yaml.getStringList(path);
        return l == null ? Collections.<String>emptyList() : l;
    }

    public List<String> body(String page) {
        List<String> l = this.yaml.getStringList(page + ".body");
        return l == null ? Collections.<String>emptyList() : l;
    }

    public List<String> footer(String page) {
        List<String> l = this.yaml.getStringList(page + ".footer");
        return l == null ? Collections.<String>emptyList() : l;
    }

    /** Reads {@code <page>-color}; returns ChatColor.BLACK when missing. */
    public ChatColor color(String page) {
        String raw = this.yaml.getString(page + "-color", "BLACK");
        try { return ChatColor.valueOf(raw.toUpperCase()); }
        catch (Throwable t) { return ChatColor.BLACK; }
    }

    /** Reads {@code <page>-style}; returns null when blank. */
    public ChatColor style(String page) {
        String raw = this.yaml.getString(page + "-style", "");
        if (raw == null || raw.isEmpty()) return null;
        try { return ChatColor.valueOf(raw.toUpperCase()); }
        catch (Throwable t) { return null; }
    }

    /* ------------------------------------------------------------------ */
    /*  Buttons                                                           */
    /* ------------------------------------------------------------------ */

    public Button button(String key) {
        String base = "buttons." + key + ".";
        return new Button(
                this.yaml.getString(base + "label", ""),
                this.yaml.getString(base + "command", ""),
                this.yaml.getString(base + "hover", ""));
    }

    public Button entry(String page, String key) {
        String base = page + ".entries." + key + ".";
        return new Button(
                this.yaml.getString(base + "label", ""),
                "",
                this.yaml.getString(base + "hover", ""));
    }

    public Button pageButton(String page, String key) {
        String base = page + ".buttons." + key + ".";
        return new Button(
                this.yaml.getString(base + "label", ""),
                "",
                this.yaml.getString(base + "hover", ""));
    }

    /* ------------------------------------------------------------------ */
    /*  Utilities                                                         */
    /* ------------------------------------------------------------------ */

    /** Static: translate '&' legacy colour codes in an arbitrary string. */
    public static String colorize(String s) {
        return ChatColor.translateAlternateColorCodes('&', s == null ? "" : s);
    }

    /** Simple %key% -> value substitution. */
    public String format(String raw, String... pairs) {
        if (raw == null) return "";
        String out = raw;
        for (int i = 0; i + 1 < pairs.length; i += 2) {
            String key = pairs[i];
            String val = pairs[i + 1] == null ? "" : pairs[i + 1];
            out = out.replace("%" + key + "%", val);
        }
        return out;
    }
}
