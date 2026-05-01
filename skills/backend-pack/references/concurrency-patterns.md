---
name: concurrency-patterns
description: 'Concurrency patterns per stack: Java virtual threads + structured concurrency, .NET Channels + Task, Node.js worker_threads + p-limit, Python asyncio + TaskGroup, Go goroutines + errgroup, Rust tokio.'
---
# Concurrency Patterns

## Java — Virtual Threads + Structured Concurrency (JDK 21+)

```java
// BAD: ExecutorService with platform threads, no error propagation
var pool = Executors.newFixedThreadPool(10);
var f1 = pool.submit(() -> fetchUser(id));
var f2 = pool.submit(() -> fetchOrders(id));
// f1.get() blocks; if f2 fails, f1 keeps running

// GOOD: Virtual threads + StructuredTaskScope
try (var scope = new StructuredTaskScope.ShutdownOnFailure()) {
    Subtask<User>   user   = scope.fork(() -> fetchUser(id));
    Subtask<Orders> orders = scope.fork(() -> fetchOrders(id));
    scope.join().throwIfFailed();           // cancel siblings on first failure
    return new Profile(user.get(), orders.get());
}
```

## .NET — Channels + Task.WhenAll

```csharp
// BAD: Fire-and-forget, swallowed exceptions
foreach (var id in ids) _ = ProcessAsync(id);

// GOOD: Bounded channel + worker tasks + cancellation
var channel = Channel.CreateBounded<string>(new BoundedChannelOptions(100) {
    FullMode = BoundedChannelFullMode.Wait,
});

var workers = Enumerable.Range(0, 4).Select(_ => Task.Run(async () => {
    await foreach (var id in channel.Reader.ReadAllAsync(ct)) {
        await ProcessAsync(id, ct);
    }
})).ToArray();

await foreach (var id in source.WithCancellation(ct))
    await channel.Writer.WriteAsync(id, ct);
channel.Writer.Complete();
await Task.WhenAll(workers); // surfaces first exception
```

## Node.js — p-limit + AbortController

```typescript
// BAD: Promise.all with 10k items → exhausts FD/memory
await Promise.all(ids.map(fetchPayment));

// GOOD: Concurrency limit + cancellation
import pLimit from 'p-limit';
const limit = pLimit(10);
const ac = new AbortController();
setTimeout(() => ac.abort(), 30_000);

const results = await Promise.all(
  ids.map(id => limit(() => fetchPayment(id, { signal: ac.signal })))
);
```

CPU-bound → use `node:worker_threads` (don't block event loop).

## Python — asyncio TaskGroup (3.11+)

```python
# BAD: gather without exception handling, no timeout
results = await asyncio.gather(*[fetch(id) for id in ids])

# GOOD: TaskGroup auto-cancels siblings on failure
async with asyncio.timeout(30):
    async with asyncio.TaskGroup() as tg:
        user_task = tg.create_task(fetch_user(id))
        orders_task = tg.create_task(fetch_orders(id))
return Profile(user_task.result(), orders_task.result())

# Bounded concurrency
sem = asyncio.Semaphore(10)
async def bounded(id): 
    async with sem: return await fetch(id)
results = await asyncio.gather(*map(bounded, ids))
```

## Go — errgroup + context

```go
// BAD: WaitGroup with shared slice; no cancel on error
var wg sync.WaitGroup
for _, id := range ids {
    wg.Add(1)
    go func(id string) { defer wg.Done(); fetch(id) }(id)
}
wg.Wait()

// GOOD: errgroup cancels siblings; SetLimit caps concurrency
g, gctx := errgroup.WithContext(ctx)
g.SetLimit(10)
for _, id := range ids {
    id := id
    g.Go(func() error {
        select {
        case <-gctx.Done(): return gctx.Err()
        default: return fetch(gctx, id)
        }
    })
}
return g.Wait()
```

## Rust — tokio JoinSet + select!

```rust
// BAD: spawn without joining; tasks leak
for id in ids { tokio::spawn(fetch(id)); }

// GOOD: JoinSet with cancellation; collect results
let mut set = tokio::task::JoinSet::new();
for id in ids { set.spawn(fetch(id)); }

let mut results = Vec::new();
while let Some(res) = set.join_next().await {
    results.push(res??); // outer ?: JoinError, inner ?: app error
}

// Race with timeout
tokio::select! {
    res = fetch(id) => res?,
    _ = tokio::time::sleep(Duration::from_secs(5)) => return Err(Timeout),
}
```

## Universal Rules

- **Always set timeout/cancellation token** for any I/O.
- **Bound concurrency** (semaphore / limit / channel capacity) — never unbounded fan-out.
- **Propagate errors** — first failure should cancel siblings (structured concurrency).
- **Don't share mutable state** without explicit sync primitives (`Mutex`, `RwLock`, channels).
- **Test with race detector** (`go test -race`, `cargo test`, `pytest --asyncio-mode=auto`).

