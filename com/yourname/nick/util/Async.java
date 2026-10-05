package com.yourname.nick.util;

import java.util.concurrent.CompletableFuture;
import org.bukkit.plugin.IllegalPluginAccessException;
import org.bukkit.plugin.Plugin;











public final class Async
{
  public static <T> CompletableFuture<T> supply(Plugin plugin, final ThrowingSupplier<T> supplier) {
    final CompletableFuture<T> future = new CompletableFuture<>();
    if (!plugin.isEnabled()) {
      future.completeExceptionally(new IllegalStateException("Plugin is not enabled"));
      return future;
    } 
    try {
      plugin.getServer().getScheduler().runTaskAsynchronously(plugin, new Runnable() {
            public void run() {
              try {
                future.complete(supplier.get());
              } catch (Throwable throwable) {
                future.completeExceptionally(throwable);
              } 
            }
          });
    } catch (IllegalPluginAccessException exception) {
      future.completeExceptionally((Throwable)exception);
    } 
    return future;
  }
  
  public static void main(Plugin plugin, Runnable task) {
    if (!plugin.isEnabled())
      return;  plugin.getServer().getScheduler().runTask(plugin, task);
  }
  
  @FunctionalInterface
  public static interface ThrowingSupplier<T> {
    T get() throws Exception;
  }
}


/* Location:              C:\Users\nasle javan\Downloads\NickSystem-1.0.0.jar!\com\yourname\nic\\util\Async.class
 * Java compiler version: 8 (52.0)
 * JD-Core Version:       1.1.3
 */