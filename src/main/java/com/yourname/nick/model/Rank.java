package com.yourname.nick.model;

import java.util.Locale;
import java.util.Optional;
import org.bukkit.ChatColor;

public enum Rank
{
  DEFAULT("DEFAULT", ChatColor.GRAY, null),
  VIP("VIP", ChatColor.GREEN, null),
  VIP_PLUS("VIP", ChatColor.GREEN, ChatColor.GOLD),
  MVP("MVP", ChatColor.AQUA, null),
  MVP_PLUS("MVP", ChatColor.AQUA, ChatColor.RED);
  
  private final String base;
  private final ChatColor color;
  private final ChatColor plusColor;
  
  Rank(String base, ChatColor color, ChatColor plusColor) {
    this.base = base;
    this.color = color;
    this.plusColor = plusColor;
  }
  
  public ChatColor nameColor() { return this.color; } public ChatColor getNameColor() {
    return this.color;
  }
  public String label() {
    return (this.plusColor == null) ? this.base : (this.base + "+");
  }

  
  public String prefix() {
    if (this == DEFAULT) return ""; 
    StringBuilder sb = new StringBuilder();
    sb.append(this.color).append('[').append(this.base);
    if (this.plusColor != null) sb.append(this.plusColor).append('+'); 
    sb.append(this.color).append(']').append(ChatColor.RESET).append(' ');
    return sb.toString();
  }
  
  public String tag() {
    if (this == DEFAULT) return ""; 
    return prefix().trim();
  }
  
  public String pickerLabel() {
    if (this == DEFAULT) return this.color + "DEFAULT"; 
    return prefix().trim();
  }
  
  public String styledName(String name) {
    return prefix() + this.color + name + ChatColor.RESET;
  }
  
  public static Optional<Rank> parse(String input) {
    if (input == null || input.trim().isEmpty()) return Optional.empty(); 
    String trimmed = input.trim();
    String normalized = trimmed.toUpperCase(Locale.ROOT).replace("+", "_PLUS");
    for (Rank rank : values()) {
      if (rank.name().equals(normalized) || rank.label().equalsIgnoreCase(trimmed)) {
        return Optional.of(rank);
      }
    } 
    return Optional.empty();
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\model\Rank.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */