package com.yourname.nick.name;

import com.yourname.nick.disguise.DisguiseRegistry;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.regex.Pattern;
import org.bukkit.Bukkit;
import org.bukkit.configuration.file.YamlConfiguration;
import org.bukkit.entity.Player;

public final class NameValidator
{
  public enum Result
  {
    VALID, INVALID_FORMAT, RESERVED, IN_USE, OWN_NAME;
  }
  private static final Pattern MOJANG_NAME = Pattern.compile("^[A-Za-z0-9_]{3,16}$");
  
  private final Set<String> reserved;
  private final List<String> reservedFragments;
  private final DisguiseRegistry registry;
  
  public NameValidator(YamlConfiguration names, DisguiseRegistry registry) {
    this.registry = registry;
    
    Set<String> lowerReserved = new HashSet<>();
    for (String value : names.getStringList("reserved")) {
      if (value != null) lowerReserved.add(value.toLowerCase(Locale.ROOT)); 
    } 
    this.reserved = Collections.unmodifiableSet(lowerReserved);
    
    List<String> fragments = new ArrayList<>();
    for (String value : names.getStringList("reserved-fragments")) {
      if (value == null)
        continue;  String trimmed = value.toLowerCase(Locale.ROOT).trim();
      if (!trimmed.isEmpty()) fragments.add(trimmed); 
    } 
    this.reservedFragments = Collections.unmodifiableList(fragments);
  }
  
  public static boolean isValidFormat(String name) {
    return (name != null && MOJANG_NAME.matcher(name).matches());
  }
  
  public Result validate(String name, Player requester) {
    if (!isValidFormat(name)) return Result.INVALID_FORMAT; 
    String lower = name.toLowerCase(Locale.ROOT);
    if (this.reserved.contains(lower)) return Result.RESERVED; 
    for (String fragment : this.reservedFragments) {
      if (lower.contains(fragment)) return Result.RESERVED; 
    } 
    if (name.equalsIgnoreCase(requester.getName())) return Result.OWN_NAME; 
    Player online = Bukkit.getPlayerExact(name);
    if (online != null && !online.getUniqueId().equals(requester.getUniqueId())) {
      return Result.IN_USE;
    }
    if (this.registry.isNickInUse(name, requester.getUniqueId())) return Result.IN_USE; 
    return Result.VALID;
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\name\NameValidator.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */