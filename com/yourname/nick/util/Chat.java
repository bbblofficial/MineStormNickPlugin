package com.yourname.nick.util;

import org.bukkit.ChatColor;





public final class Chat
{
  public static String color(String input) {
    return ChatColor.translateAlternateColorCodes('&', (input == null) ? "" : input);
  }
  
  public static String strip(String input) {
    return ChatColor.stripColor(color(input));
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nic\\util\Chat.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */