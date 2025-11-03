<?php

declare(strict_types=1);

namespace Framework\View;

final class ViewFactory
{
    private TemplateEngine $engine;

    public function __construct(private readonly string $viewPath, private readonly string $cachePath)
    {
        $this->engine = new TemplateEngine($viewPath, $cachePath);
    }

    public function make(string $view, array $data = []): string
    {
        return $this->engine->render($view, $data);
    }
}
