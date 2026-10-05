package com.yourname.nick.util;

import com.yourname.nick.model.DisguiseProfile;
import java.util.Collection;









public final class NameMasker
{
  public static String mask(String message, Collection<DisguiseProfile> profiles) {
    if (message == null) return null; 
    String result = message;
    for (DisguiseProfile profile : profiles) {
      if (profile == null || !profile.isActive() || 
        profile.getRealName() == null || profile.getRealName().isEmpty())
        continue;  result = result.replace(profile.getRealName(), profile.getNickname());
    } 
    return result;
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nic\\util\NameMasker.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */