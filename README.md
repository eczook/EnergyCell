# EnergyCell 0.1.0

An experimental beginner-friendly web language prototype. `.ec` files describe page content, simple styling, and click interactions.

## Windows requirements
Install Python 3.10+ from https://www.python.org/downloads/ and enable **Add Python to PATH**. No Visual Studio or third-party Python packages are required.

## Try it
Open PowerShell in this folder:

```powershell
py ec.py check examples\hello.ec
py ec.py build examples\hello.ec -o hello.html
py ec.py run examples\hello.ec
```

`run` opens a local preview at `http://127.0.0.1:8000`; press Ctrl+C to stop it. Or use `.\ec.bat run examples\hello.ec`.

## Example
```text
page {
    title "My Website"
    style {
        background: "#202124"
        color: "white"
    }
    heading "Welcome!"
    text "Made with EnergyCell."
    button "Click me" {
        on click {
            show "It works!"
        }
    }
}
```

## What's in this prototype
- Lexer/parser for the supported `.ec` subset
- HTML/CSS/JS generation with escaped text
- `check`, `build`, and `run` commands
- Example and automated tests

## Limitations
This is a Python-based prototype, not a native compiler. It currently generates static browser output; PHP-like backend features, database access, and native apps are not implemented. Syntax may change before a stable release.

## License
MIT; see `LICENSE`.
