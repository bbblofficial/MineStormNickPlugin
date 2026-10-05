/*    */ package com.yourname.nick.util;
/*    */ 
/*    */ import java.util.concurrent.CompletableFuture;
/*    */ import org.bukkit.plugin.IllegalPluginAccessException;
/*    */ import org.bukkit.plugin.Plugin;
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ 
/*    */ public final class Async
/*    */ {
/*    */   public static <T> CompletableFuture<T> supply(Plugin plugin, final ThrowingSupplier<T> supplier) {
/* 20 */     final CompletableFuture<T> future = new CompletableFuture<>();
/* 21 */     if (!plugin.isEnabled()) {
/* 22 */       future.completeExceptionally(new IllegalStateException("Plugin is not enabled"));
/* 23 */       return future;
/*    */     } 
/*    */     try {
/* 26 */       plugin.getServer().getScheduler().runTaskAsynchronously(plugin, new Runnable() {
/*    */             public void run() {
/*    */               try {
/* 29 */                 future.complete(supplier.get());
/* 30 */               } catch (Throwable throwable) {
/* 31 */                 future.completeExceptionally(throwable);
/*    */               } 
/*    */             }
/*    */           });
/* 35 */     } catch (IllegalPluginAccessException exception) {
/* 36 */       future.completeExceptionally((Throwable)exception);
/*    */     } 
/* 38 */     return future;
/*    */   }
/*    */   
/*    */   public static void main(Plugin plugin, Runnable task) {
/* 42 */     if (!plugin.isEnabled())
/* 43 */       return;  plugin.getServer().getScheduler().runTask(plugin, task);
/*    */   }
/*    */   
/*    */   @FunctionalInterface
/*    */   public static interface ThrowingSupplier<T> {
/*    */     T get() throws Exception;
/*    */   }
/*    */ }


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nic\\util\Async.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */