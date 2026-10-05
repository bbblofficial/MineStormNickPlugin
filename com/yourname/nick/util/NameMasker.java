/*    */ package com.yourname.nick.util;
/*    */ 
/*    */ import com.yourname.nick.model.DisguiseProfile;
/*    */ import java.util.Collection;
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class NameMasker
/*    */ {
/*    */   public static String mask(String message, Collection<DisguiseProfile> profiles) {
/* 17 */     if (message == null) return null; 
/* 18 */     String result = message;
/* 19 */     for (DisguiseProfile profile : profiles) {
/* 20 */       if (profile == null || !profile.isActive() || 
/* 21 */         profile.getRealName() == null || profile.getRealName().isEmpty())
/* 22 */         continue;  result = result.replace(profile.getRealName(), profile.getNickname());
/*    */     } 
/* 24 */     return result;
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nic\\util\NameMasker.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */