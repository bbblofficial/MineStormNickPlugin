package com.yourname.nick.model;public final class SkinData {
  private static final int MAX_LABEL = 64;
  
  public enum Type {
    NORMAL, DEFAULT, CUSTOM;
  }
  
  private static final SkinData NORMAL_SKIN = new SkinData(Type.NORMAL, "", "", "");
  private static final SkinData DEFAULT_SKIN = new SkinData(Type.DEFAULT, "", "", "");
  
  private final Type type;
  private final String value;
  private final String signature;
  private final String label;
  
  public SkinData(Type type, String value, String signature, String label) {
    this.type = type;
    this.value = value;
    this.signature = signature;
    this.label = label;
  }
  
  public static SkinData normal() { return NORMAL_SKIN; } public static SkinData defaultSkin() {
    return DEFAULT_SKIN;
  }
  public static SkinData custom(String value, String signature, String label) {
    String safe = (label == null) ? "CUSTOM" : label;
    if (safe.length() > 64) safe = safe.substring(0, 64); 
    return new SkinData(Type.CUSTOM, value, (signature == null) ? "" : signature, safe);
  }
  
  public static SkinData fromStorage(String source, String value, String signature) {
    if (value != null && !value.isEmpty()) return custom(value, signature, source); 
    if ("DEFAULT".equals(source)) return defaultSkin(); 
    return normal();
  }
  
  public Type type() { return this.type; }
  public Type getType() { return this.type; }
  public String value() { return this.value; }
  public String getValue() { return this.value; }
  public String signature() { return this.signature; }
  public String getSignature() { return this.signature; }
  public String label() { return this.label; } public String getLabel() {
    return this.label;
  }
  public String sourceKey() {
    if (this.type == Type.NORMAL) return "NORMAL"; 
    if (this.type == Type.DEFAULT) return "DEFAULT"; 
    return this.label;
  }
  
  public String displayLabel() {
    if (this.type == Type.NORMAL) return "your normal skin"; 
    if (this.type == Type.DEFAULT) return "Steve/Alex skin"; 
    int separator = this.label.indexOf(':');
    return (separator >= 0 && separator < this.label.length() - 1) ? this.label.substring(separator + 1) : this.label;
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nick\model\SkinData.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */