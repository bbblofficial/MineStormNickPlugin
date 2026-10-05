/*    */ package com.yourname.nick.model;public final class SkinData {
/*    */   private static final int MAX_LABEL = 64;
/*    */   
/*    */   public enum Type {
/*  5 */     NORMAL, DEFAULT, CUSTOM;
/*    */   }
/*    */   
/*  8 */   private static final SkinData NORMAL_SKIN = new SkinData(Type.NORMAL, "", "", "");
/*  9 */   private static final SkinData DEFAULT_SKIN = new SkinData(Type.DEFAULT, "", "", "");
/*    */   
/*    */   private final Type type;
/*    */   private final String value;
/*    */   private final String signature;
/*    */   private final String label;
/*    */   
/*    */   public SkinData(Type type, String value, String signature, String label) {
/* 17 */     this.type = type;
/* 18 */     this.value = value;
/* 19 */     this.signature = signature;
/* 20 */     this.label = label;
/*    */   }
/*    */   
/* 23 */   public static SkinData normal() { return NORMAL_SKIN; } public static SkinData defaultSkin() {
/* 24 */     return DEFAULT_SKIN;
/*    */   }
/*    */   public static SkinData custom(String value, String signature, String label) {
/* 27 */     String safe = (label == null) ? "CUSTOM" : label;
/* 28 */     if (safe.length() > 64) safe = safe.substring(0, 64); 
/* 29 */     return new SkinData(Type.CUSTOM, value, (signature == null) ? "" : signature, safe);
/*    */   }
/*    */   
/*    */   public static SkinData fromStorage(String source, String value, String signature) {
/* 33 */     if (value != null && !value.isEmpty()) return custom(value, signature, source); 
/* 34 */     if ("DEFAULT".equals(source)) return defaultSkin(); 
/* 35 */     return normal();
/*    */   }
/*    */   
/* 38 */   public Type type() { return this.type; }
/* 39 */   public Type getType() { return this.type; }
/* 40 */   public String value() { return this.value; }
/* 41 */   public String getValue() { return this.value; }
/* 42 */   public String signature() { return this.signature; }
/* 43 */   public String getSignature() { return this.signature; }
/* 44 */   public String label() { return this.label; } public String getLabel() {
/* 45 */     return this.label;
/*    */   }
/*    */   public String sourceKey() {
/* 48 */     if (this.type == Type.NORMAL) return "NORMAL"; 
/* 49 */     if (this.type == Type.DEFAULT) return "DEFAULT"; 
/* 50 */     return this.label;
/*    */   }
/*    */   
/*    */   public String displayLabel() {
/* 54 */     if (this.type == Type.NORMAL) return "your normal skin"; 
/* 55 */     if (this.type == Type.DEFAULT) return "Steve/Alex skin"; 
/* 56 */     int separator = this.label.indexOf(':');
/* 57 */     return (separator >= 0 && separator < this.label.length() - 1) ? this.label.substring(separator + 1) : this.label;
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\model\SkinData.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */