<?php

declare(strict_types=1);

namespace Framework\Support;

final class Container
{
    /** @var array<string, callable|object> */
    private array $bindings = [];

    /** @var array<string, bool> */
    private array $resolved = [];

    public function singleton(string $id, callable $concrete): void
    {
        $this->bindings[$id] = $concrete;
    }

    public function bind(string $id, callable $concrete): void
    {
        $this->bindings[$id] = $concrete;
    }

    public function get(string $id): mixed
    {
        if (array_key_exists($id, $this->bindings) && is_object($this->bindings[$id]) && !$this->bindings[$id] instanceof \Closure) {
            return $this->bindings[$id];
        }

        if (!isset($this->bindings[$id])) {
            throw new \InvalidArgumentException("Service '{$id}' is not bound in the container.");
        }

        if (!isset($this->resolved[$id])) {
            $this->bindings[$id] = ($this->bindings[$id])();
            $this->resolved[$id] = true;
        }

        return $this->bindings[$id];
    }
}
