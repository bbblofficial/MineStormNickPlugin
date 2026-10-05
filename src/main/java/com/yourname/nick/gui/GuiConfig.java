package com.yourname.nick.gui;

import java.io.File;
import java.util.Collections;
import java.util.List;
import org.bukkit.ChatColor;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.plugin.java.JavaPlugin;

/** Typed reader for gui.yml. All strings are colour-translated on read. */
public final class GuiConfig {

    public static final class Button {
        private final String label;
        private final String command;
        private final String hover;
        public Button(String label, String command, String hover) {
            this.label = colorize(label);
            this.command = command == null ? "" : command;
            this.hover = colorize(hover);
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

    public String title()  { return colorize(this.yaml.getString("book.title",  "Nickname Setup")); }
    public String author() { return colorize(this.yaml.getString("book.author", "MineStormNickSystem")); }

    public String get(String path) {
        return colorize(this.yaml.getString(path, ""));
    }

    public List<String> list(String path) {
        return colorizeList(this.yaml.getStringList(path));
    }
    public List<String> body(String page) {
        return colorizeList(this.yaml.getStringList(page + ".body"));
    }
    public List<String> footer(String page) {
        return colorizeList(this.yaml.getStringList(page + ".footer"));
    }

    public ChatColor color(String page) {
        String raw = this.yaml.getString(page + "-color", "BLACK");
        try { return ChatColor.valueOf(raw.toUpperCase()); }
        catch (Throwable t) { return ChatColor.BLACK; }
    }
    public ChatColor style(String page) {
        String raw = this.yaml.getString(page + "-style", "");
        if (raw == null || raw.isEmpty()) return null;
        try { return ChatColor.valueOf(raw.toUpperCase()); }
        catch (Throwable t) { return null; }
    }

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

    public static String colorize(String s) {
        return ChatColor.translateAlternateColorCodes('&', s == null ? "" : s);
    }
    private static List<String> colorizeList(List<String> in) {
        if (in == null) return Collections.emptyList();
        java.util.List<String> out = new java.util.ArrayList<String>(in.size());
        for (String s : in) out.add(colorize(s));
        return out;
    }

    public String format(String raw, String... pairs) {
        if (raw == null) return "";
        String out = raw;
        for (int i = 0; i + 1 < pairs.length; i += 2) {
            String key = pairs[i];
            String val = pairs[i + 1] == null ? "" : pairs[i + 1];
            out = out.replace("%" + key + "%", val);
        }
        return colorize(out);
    }
}
