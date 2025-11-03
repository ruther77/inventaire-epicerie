<?php

declare(strict_types=1);

namespace Framework\View;

use Framework\Application\Application;
use RuntimeException;

final class TemplateEngine
{
    private array $sections = [];

    private array $sectionStack = [];

    private ?string $layout = null;

    private array $componentStack = [];

    public function __construct(private readonly string $viewPath, private readonly string $cachePath)
    {
        if (!is_dir($cachePath)) {
            mkdir($cachePath, 0777, true);
        }
    }

    public function render(string $view, array $data = []): string
    {
        $compiled = $this->compile($view);

        $errors = Application::getInstance()->session()->errors();

        $__env = $this;
        extract($data, EXTR_SKIP);

        ob_start();
        include $compiled;
        $content = ob_get_clean();

        if ($this->layout !== null) {
            $layout = $this->layout;
            $this->layout = null;
            if (!isset($this->sections['content'])) {
                $this->sections['content'] = $content;
            }
            $content = $this->render($layout, array_merge($data, ['content' => $content]));
        }

        $this->flushState();

        return $content;
    }

    public function setLayout(string $layout): void
    {
        $this->layout = $layout;
    }

    public function startSection(string $section): void
    {
        $this->sectionStack[] = $section;
        ob_start();
    }

    public function stopSection(): void
    {
        $section = array_pop($this->sectionStack);
        $this->sections[$section] = ob_get_clean();
    }

    public function yieldSection(string $section, string $default = ''): string
    {
        if ($section === 'content' && isset($this->sections[$section])) {
            return $this->sections[$section];
        }

        return $this->sections[$section] ?? $default;
    }

    public function include(string $view, array $data = []): string
    {
        return $this->render($view, $data);
    }

    public function startComponent(string $view, array $data = []): void
    {
        $this->componentStack[] = [$view, $data];
        $this->sectionStack[] = '__component';
        ob_start();
    }

    public function renderComponent(): string
    {
        $content = ob_get_clean();
        array_pop($this->sectionStack);

        [$view, $data] = array_pop($this->componentStack);

        return $this->render($view, array_merge($data, ['slot' => $content]));
    }

    public function hasError(string $key): bool
    {
        $errors = Application::getInstance()->session()->errors();

        return isset($errors[$key]);
    }

    public function error(string $key, string $glue = '<br>'): string
    {
        $errors = Application::getInstance()->session()->errors();

        return isset($errors[$key]) ? implode($glue, array_map(static fn (string $message): string => trans($message), $errors[$key])) : '';
    }

    private function flushState(): void
    {
        $this->sections = [];
        $this->sectionStack = [];
        $this->componentStack = [];
        $this->layout = null;
    }

    private function compile(string $view): string
    {
        $viewFile = rtrim($this->viewPath, '/') . '/' . str_replace('.', '/', $view) . '.blade.php';
        if (!is_file($viewFile)) {
            throw new RuntimeException("View '{$view}' not found.");
        }

        $hash = sha1($viewFile . filemtime($viewFile));
        $compiled = rtrim($this->cachePath, '/') . '/' . $hash . '.php';

        if (!is_file($compiled)) {
            $contents = file_get_contents($viewFile);
            $contents = $this->compileStatements($contents);
            file_put_contents($compiled, $contents);
        }

        return $compiled;
    }

    private function compileStatements(string $value): string
    {
        $patterns = [
            '/{{\s*(.+?)\s*}}/' => '<?php echo e($1); ?>',
            '/{!!\s*(.+?)\s*!!}/' => '<?php echo $1; ?>',
            '/@extends\((.+)\)/' => '<?php $__env->setLayout($1); ?>',
            '/@section\((.+)\)/' => '<?php $__env->startSection($1); ?>',
            '/@endsection/' => '<?php $__env->stopSection(); ?>',
            '/@yield\((.+)\)/' => '<?php echo $__env->yieldSection($1); ?>',
            '/@endcomponent/' => '<?php echo $__env->renderComponent(); ?>',
            '/@csrf/' => '<?php echo csrf_field(); ?>',
            '/@foreach\s*\((.+)\)/' => '<?php foreach ($1): ?>',
            '/@endforeach/' => '<?php endforeach; ?>',
            '/@if\s*\((.+)\)/' => '<?php if ($1): ?>',
            '/@elseif\s*\((.+)\)/' => '<?php elseif ($1): ?>',
            '/@else/' => '<?php else: ?>',
            '/@endif/' => '<?php endif; ?>',
            '/@error\((.+)\)/' => '<?php if ($__env->hasError($1)): ?>',
            '/@enderror/' => '<?php endif; ?>',
        ];

        foreach ($patterns as $pattern => $replacement) {
            $value = preg_replace($pattern, $replacement, $value);
        }

        $value = preg_replace_callback('/@include\((.+)\)/', function (array $matches): string {
            [$view, $data] = $this->splitArguments($matches[1]);

            return "<?php echo \$__env->include({$view}, {$data}); ?>";
        }, $value);

        $value = preg_replace_callback('/@component\((.+)\)/', function (array $matches): string {
            [$view, $data] = $this->splitArguments($matches[1]);

            return "<?php \$__env->startComponent({$view}, {$data}); ?>";
        }, $value);

        return $value;
    }

    /**
     * @return array{0:string,1:string}
     */
    private function splitArguments(string $expression): array
    {
        $depth = 0;
        $length = strlen($expression);
        for ($i = 0; $i < $length; $i++) {
            $char = $expression[$i];
            if ($char === '(' || $char === '[') {
                $depth++;
            } elseif ($char === ')' || $char === ']') {
                $depth--;
            } elseif ($char === ',' && $depth === 0) {
                $view = trim(substr($expression, 0, $i));
                $data = trim(substr($expression, $i + 1));

                return [$view, $data === '' ? '[]' : $data];
            }
        }

        $expression = trim($expression);

        return [$expression, '[]'];
    }
}
