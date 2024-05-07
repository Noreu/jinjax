import time
from pathlib import Path

import jinja2
import pytest
from jinja2.exceptions import TemplateSyntaxError
from markupsafe import Markup

import jinjax


@pytest.mark.parametrize("autoescape", [True, False])
def test_render_simple(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Greeting.jinja").write_text(
        """
{#def message #}
<div class="greeting [&_a]:flex">{{ message }}</div>
    """
    )
    html = catalog.render("Greeting", message="Hello world!")
    assert html == Markup('<div class="greeting [&_a]:flex">Hello world!</div>')


@pytest.mark.parametrize("autoescape", [True, False])
def test_render_source(catalog, autoescape):
    catalog.jinja_env.autoescape = autoescape

    source = """
{#def message #}
<div class="greeting [&_a]:flex">{{ message }}</div>
    """
    html = catalog.render("Greeting", message="Hello world!", __source=source)
    assert html == Markup('<div class="greeting [&_a]:flex">Hello world!</div>')


@pytest.mark.parametrize("autoescape", [True, False])
def test_render_content(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Card.jinja").write_text(
        """
<section class="card">
{{ content }}
</section>
    """
    )

    content = '<button type="button">Close</button>'
    html = catalog.render("Card", __content=content)
    print(html)
    assert (
        html
        == Markup(f"""
<section class="card">
{content}
</section>""".strip())
    )


@pytest.mark.parametrize("autoescape", [True, False])
@pytest.mark.parametrize(
    "source, expected",
    [
        ("<Title>Hi</Title><Title>Hi</Title>", "<h1>Hi</h1><h1>Hi</h1>"),
        ("<Icon /><Icon />", '<i class="icon"></i><i class="icon"></i>'),
        ("<Title>Hi</Title><Icon />", '<h1>Hi</h1><i class="icon"></i>'),
        ("<Icon /><Title>Hi</Title>", '<i class="icon"></i><h1>Hi</h1>'),
    ],
)
def test_render_mix_of_contentful_and_contentless_components(
    catalog, folder, source, expected, autoescape,
):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Icon.jinja").write_text('<i class="icon"></i>')
    (folder / "Title.jinja").write_text("<h1>{{ content }}</h1>")
    (folder / "Page.jinja").write_text(source)

    html = catalog.render("Page")
    assert html == Markup(expected)


@pytest.mark.parametrize("autoescape", [True, False])
def test_composition(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Greeting.jinja").write_text(
        """
{#def message #}
<div class="greeting [&_a]:flex">{{ message }}</div>
"""
    )

    (folder / "CloseBtn.jinja").write_text(
        """
{#def disabled=False -#}
<button type="button"{{ " disabled" if disabled else "" }}>&times;</button>
"""
    )

    (folder / "Card.jinja").write_text(
        """
<section class="card">
{{ content }}
<CloseBtn disabled />
</section>
"""
    )

    (folder / "Page.jinja").write_text(
        """
{#def message #}
<Card>
<Greeting message={message} />
<button type="button">Close</button>
</Card>
"""
    )

    html = catalog.render("Page", message="Hello")
    print(html)
    assert (
        """
<section class="card">
<div class="greeting [&_a]:flex">Hello</div>
<button type="button">Close</button>
<button type="button" disabled>&times;</button>
</section>
""".strip()
        in html
    )


@pytest.mark.parametrize("autoescape", [True, False])
def test_just_properties(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Lorem.jinja").write_text(
        """
{#def ipsum=False #}
<p>lorem {{ "ipsum" if ipsum else "lorem" }}</p>
"""
    )

    (folder / "Layout.jinja").write_text(
        """
<main>
{{ content }}
</main>
"""
    )

    (folder / "Page.jinja").write_text(
        """
<Layout>
<Lorem ipsum />
<p>meh</p>
<Lorem />
</Layout>
"""
    )

    html = catalog.render("Page")
    print(html)
    assert (
        """
<main>
<p>lorem ipsum</p>
<p>meh</p>
<p>lorem lorem</p>
</main>
""".strip()
        in html
    )


@pytest.mark.parametrize("autoescape", [True, False])
def test_render_assets(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Greeting.jinja").write_text(
        """
{#def message #}
{#css greeting.css, http://example.com/super.css #}
{#js greeting.js #}
<div class="greeting [&_a]:flex">{{ message }}</div>
"""
    )

    (folder / "Card.jinja").write_text(
        """
{#css https://somewhere.com/style.css, card.css #}
{#js card.js, shared.js #}
<section class="card">
{{ content }}
</section>
"""
    )

    (folder / "Layout.jinja").write_text(
        """
<html>
{{ catalog.render_assets() }}
{{ content }}
</html>
"""
    )

    (folder / "Page.jinja").write_text(
        """
{#def message #}
{#js https://somewhere.com/blabla.js, shared.js #}
<Layout>
<Card>
<Greeting message={message} />
<button type="button">Close</button>
</Card>
</Layout>
"""
    )

    html = catalog.render("Page", message="Hello")
    print(html)
    assert (
        """
<html>
<link rel="stylesheet" href="https://somewhere.com/style.css">
<link rel="stylesheet" href="/static/components/card.css">
<link rel="stylesheet" href="/static/components/greeting.css">
<link rel="stylesheet" href="http://example.com/super.css">
<script type="module" src="https://somewhere.com/blabla.js"></script>
<script type="module" src="/static/components/shared.js"></script>
<script type="module" src="/static/components/card.js"></script>
<script type="module" src="/static/components/greeting.js"></script>
<section class="card">
<div class="greeting [&_a]:flex">Hello</div>
<button type="button">Close</button>
</section>
</html>
""".strip()
        in html
    )


@pytest.mark.parametrize("autoescape", [True, False])
def test_global_values(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Global.jinja").write_text("""{{ globalvar }}""")
    message = "Hello world!"
    catalog.jinja_env.globals["globalvar"] = message
    html = catalog.render("Global")
    print(html)
    assert message in html


@pytest.mark.parametrize("autoescape", [True, False])
def test_required_attr_are_required(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Greeting.jinja").write_text(
        """
{#def message #}
<div class="greeting">{{ message }}</div>
"""
    )

    with pytest.raises(jinjax.MissingRequiredArgument):
        catalog.render("Greeting")


@pytest.mark.parametrize("autoescape", [True, False])
def test_subfolder(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    sub = folder / "UI"
    sub.mkdir()
    (folder / "Meh.jinja").write_text("<UI.Tab>Meh</UI.Tab>")
    (sub / "Tab.jinja").write_text('<div class="tab">{{ content }}</div>')

    html = catalog.render("Meh")
    assert html == Markup('<div class="tab">Meh</div>')


@pytest.mark.parametrize("autoescape", [True, False])
def test_default_attr(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Greeting.jinja").write_text(
        """
{#def message="Hello", world=False #}
<div>{{ message }}{% if world %} World{% endif %}</div>
"""
    )

    (folder / "Page.jinja").write_text(
        """
<Greeting />
<Greeting message="Hi" />
<Greeting world={False} />
<Greeting world={True} />
<Greeting world />
"""
    )

    html = catalog.render("Page", message="Hello")
    print(html)
    assert (
        """
<div>Hello</div>
<div>Hi</div>
<div>Hello</div>
<div>Hello World</div>
<div>Hello World</div>
""".strip()
        in html
    )


@pytest.mark.parametrize("autoescape", [True, False])
def test_raw_content(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Code.jinja").write_text(
        """
<pre class="code">
{{ content|e }}
</pre>
"""
    )

    (folder / "Page.jinja").write_text(
        """
<Code>
{% raw %}
{#def message="Hello", world=False #}
<Header />
<div>{{ message }}{% if world %} World{% endif %}</div>
{% endraw %}
</Code>
"""
    )

    html = catalog.render("Page")
    print(html)
    assert (
        """
<pre class="code">
{#def message=&#34;Hello&#34;, world=False #}
&lt;Header /&gt;
&lt;div&gt;{{ message }}{% if world %} World{% endif %}&lt;/div&gt;
</pre>
""".strip()
        in html
    )


@pytest.mark.parametrize("autoescape", [True, False])
def test_multiple_raw(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "C.jinja").write_text(
        """
<div {{ attrs.render() }}></div>
"""
    )

    (folder / "Page.jinja").write_text(
        """
<C id="1" />
{% raw -%}
<C id="2" />
{%- endraw %}
<C id="3" />
{% raw %}<C id="4" />{% endraw %}
<C id="5" />
"""
    )

    html = catalog.render("Page", message="Hello")
    print(html)
    assert (
        """
<div id="1"></div>
&lt;C id=&#34;2&#34; /&gt;
<div id="3"></div>
&lt;C id=&#34;4&#34; /&gt;
<div id="5"></div>
""".strip()
        in html
    )


@pytest.mark.parametrize("autoescape", [True, False])
def test_check_for_unclosed(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Lorem.jinja").write_text(
        """
{#def ipsum=False #}
<p>lorem {{ "ipsum" if ipsum else "lorem" }}</p>
"""
    )

    (folder / "Page.jinja").write_text(
        """
<main>
<Lorem ipsum>
</main>
"""
    )
    with pytest.raises(TemplateSyntaxError):
        try:
            catalog.render("Page")
        except TemplateSyntaxError as err:
            print(err)
            raise


@pytest.mark.parametrize("autoescape", [True, False])
def test_dict_as_attr(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "CitiesList.jinja").write_text(
        """
{#def cities #}
{% for city, country in cities.items() -%}
<p>{{ city }}, {{ country }}</p>
{%- endfor %}
"""
    )

    (folder / "Page.jinja").write_text(
        """
<CitiesList cities={{
    "Lima": "Peru",
    "New York": "USA",
}}/>
"""
    )

    html = catalog.render("Page")
    assert html == Markup("<p>Lima, Peru</p><p>New York, USA</p>")


@pytest.mark.parametrize("autoescape", [True, False])
def test_cleanup_assets(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Layout.jinja").write_text(
        """
<html>
{{ catalog.render_assets() }}
{{ content }}
</html>
"""
    )

    (folder / "Foo.jinja").write_text(
        """
{#js foo.js #}
<Layout>
<p>Foo</p>
</Layout>
"""
    )

    (folder / "Bar.jinja").write_text(
        """
{#js bar.js #}
<Layout>
<p>Bar</p>
</Layout>
"""
    )

    html = catalog.render("Foo")
    print(html, "\n")
    assert (
        """
<html>
<script type="module" src="/static/components/foo.js"></script>
<p>Foo</p>
</html>
""".strip()
        in html
    )

    html = catalog.render("Bar")
    print(html)
    assert (
        """
<html>
<script type="module" src="/static/components/bar.js"></script>
<p>Bar</p>
</html>
""".strip()
        in html
    )


@pytest.mark.parametrize("autoescape", [True, False])
def test_do_not_mess_with_external_jinja_env(folder_t, folder, autoescape):

    """https://github.com/jpsca/jinjax/issues/19"""
    (folder_t / "greeting.html").write_text("Jinja still works")
    (folder / "Greeting.jinja").write_text("JinjaX works")

    jinja_env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(folder_t),
        extensions=["jinja2.ext.i18n"],
    )
    jinja_env.globals = {"glo": "bar"}
    jinja_env.filters = {"fil": lambda x: x}
    jinja_env.tests = {"tes": lambda x: x}
    jinja_env.autoescape = autoescape

    catalog = jinjax.Catalog(
        jinja_env=jinja_env,
        extensions=["jinja2.ext.debug"],
        globals={"xglo": "foo"},
        filters={"xfil": lambda x: x},
        tests={"xtes": lambda x: x},
    )
    catalog.add_folder(folder)

    html = catalog.render("Greeting")
    assert html == Markup("JinjaX works")

    assert catalog.jinja_env.globals["catalog"] == catalog
    assert catalog.jinja_env.globals["glo"] == "bar"
    assert catalog.jinja_env.globals["xglo"] == "foo"
    assert catalog.jinja_env.filters["fil"]
    assert catalog.jinja_env.filters["xfil"]
    assert catalog.jinja_env.tests["tes"]
    assert catalog.jinja_env.tests["xtes"]
    assert "jinja2.ext.InternationalizationExtension" in catalog.jinja_env.extensions
    assert "jinja2.ext.DebugExtension" in catalog.jinja_env.extensions
    assert "jinja2.ext.ExprStmtExtension" in catalog.jinja_env.extensions

    tmpl = jinja_env.get_template("greeting.html")
    assert tmpl.render() == "Jinja still works"

    assert jinja_env.globals["catalog"] == catalog
    assert jinja_env.globals["glo"] == "bar"
    assert "xglo" not in jinja_env.globals
    assert jinja_env.filters["fil"]
    assert "xfil" not in jinja_env.filters
    assert jinja_env.tests["tes"]
    assert "xtes" not in jinja_env.tests
    assert "jinja2.ext.InternationalizationExtension" in jinja_env.extensions
    assert "jinja2.ext.DebugExtension" not in jinja_env.extensions


@pytest.mark.parametrize("autoescape", [True, False])
def test_auto_reload(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Layout.jinja").write_text(
        """
<html>
{{ content }}
</html>
"""
    )

    (folder / "Foo.jinja").write_text(
        """
<Layout>
<p>Foo</p>
<Bar></Bar>
</Layout>
"""
    )

    bar_file = folder / "Bar.jinja"
    bar_file.write_text("<p>Bar</p>")

    html1 = catalog.render("Foo")
    print(bar_file.stat().st_mtime)
    print(html1, "\n")
    assert (
        """
<html>
<p>Foo</p>
<p>Bar</p>
</html>
""".strip()
        in html1
    )

    # Give it some time so the st_mtime are different
    time.sleep(0.1)

    catalog.auto_reload = False
    bar_file.write_text("<p>Ignored</p>")
    print(bar_file.stat().st_mtime)
    html2 = catalog.render("Foo")
    print(html2, "\n")

    catalog.auto_reload = True
    bar_file.write_text("<p>Updated</p>")
    print(bar_file.stat().st_mtime)
    html3 = catalog.render("Foo")
    print(html3, "\n")

    assert html1 == html2
    assert (
        """
<html>
<p>Foo</p>
<p>Updated</p>
</html>
""".strip()
        in html3
    )


@pytest.mark.parametrize("autoescape", [True, False])
def test_subcomponents(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    """Issue https://github.com/jpsca/jinjax/issues/32"""
    (folder / "Page.jinja").write_text(
        """
{#def message #}
<html>
<p>lorem ipsum</p>
<Subcomponent />
{{ message }}
</html>
"""
    )

    (folder / "Subcomponent.jinja").write_text(
        """
<p>foo bar</p>
"""
    )

    html = catalog.render("Page", message="<3")

    if autoescape:
        expected = """
<html>
<p>lorem ipsum</p>
<p>foo bar</p>
&lt;3
</html>"""
    else:
        expected = """
<html>
<p>lorem ipsum</p>
<p>foo bar</p>
<3
</html>"""

    assert html == Markup(expected.strip())


@pytest.mark.parametrize("autoescape", [True, False])
def test_fingerprint_assets(catalog, folder: Path, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Layout.jinja").write_text(
        """
<html>
{{ catalog.render_assets() }}
{{ content }}
</html>
"""
    )

    (folder / "Page.jinja").write_text(
        """
{#css app.css, http://example.com/super.css #}
{#js app.js #}
<Layout>Hi</Layout>
"""
    )

    (folder / "app.css").write_text("...")

    catalog.fingerprint = True
    html = catalog.render("Page", message="Hello")
    print(html)

    assert 'src="/static/components/app.js"' in html
    assert 'href="/static/components/app-' in html
    assert 'href="http://example.com/super.css' in html


@pytest.mark.parametrize("autoescape", [True, False])
def test_colon_in_attrs(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "C.jinja").write_text(
        """
<div {{ attrs.render() }}></div>
"""
    )

    (folder / "Page.jinja").write_text(
        """
<C hx-on:click="show = !show" />
"""
    )

    html = catalog.render("Page", message="Hello")
    print(html)
    assert """<div hx-on:click="show = !show"></div>""" in html


@pytest.mark.parametrize("autoescape", [True, False])
def test_template_globals(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Input.jinja").write_text(
        """
{# def name, value #}<input type="text" name="{{name}}" value="{{value}}">
"""
    )
    (folder / "CsrfToken.jinja").write_text(
        """
<input type="hidden" name="csrft" value="{{csrf_token}}">
"""
    )
    (folder / "Form.jinja").write_text(
        """
<form><CsrfToken/>{{content}}</form>
"""
    )

    (folder / "Page.jinja").write_text(
        """
{# def value #}
<Form><Input name="foo" value={value}/></Form>
"""
    )

    html = catalog.render("Page", value="bar", __globals={"csrf_token": "abc"})
    print(html)
    assert """<input type="hidden" name="csrft" value="abc">""" in html


@pytest.mark.parametrize("autoescape", [True, False])
def test_template_globals_update_cache(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "CsrfToken.jinja").write_text(
        """
<input type="hidden" name="csrft" value="{{csrf_token}}">
"""
    )
    (folder / "Page.jinja").write_text("""<CsrfToken/>""")

    html = catalog.render("Page", __globals={"csrf_token": "abc"})
    print(html)
    assert """<input type="hidden" name="csrft" value="abc">""" in html

    html = catalog.render("Page", __globals={"csrf_token": "xyz"})
    print(html)
    assert """<input type="hidden" name="csrft" value="xyz">""" in html


@pytest.mark.parametrize("autoescape", [True, False])
def test_alpine_sintax(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Greeting.jinja").write_text("""
{#def message #}
<button @click="alert('{{ message }}')">Say Hi</button>""")

    html = catalog.render("Greeting", message="Hello world!")
    print(html)
    expected = """<button @click="alert('Hello world!')">Say Hi</button>"""
    assert html == Markup(expected)


@pytest.mark.parametrize("autoescape", [True, False])
def test_alpine_sintax_in_component(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Button.jinja").write_text(
        """<button {{ attrs.render() }}>{{ content }}</button>"""
    )

    (folder / "Greeting.jinja").write_text(
        """<Button @click="alert('Hello world!')">Say Hi</Button>"""
    )

    html = catalog.render("Greeting")
    print(html)
    expected = """<button @click="alert('Hello world!')">Say Hi</button>"""
    assert html == Markup(expected)


@pytest.mark.parametrize("autoescape", [True, False])
def test_autoescaped_attrs(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "CheckboxItem.jinja").write_text(
        """<div {{ attrs.render(class="relative") }}></div>"""
    )

    (folder / "Page.jinja").write_text(
        """<CheckboxItem class="border border-red-500" />"""
    )

    html = catalog.render("Page")
    print(html)
    expected = """<div class="border border-red-500 relative"></div>"""
    assert html == Markup(expected)


@pytest.mark.parametrize("autoescape", [True, False])
def test_auto_load_assets_with_same_name(catalog, folder, autoescape):
    catalog.jinja_env.autoescape = autoescape

    (folder / "Layout.jinja").write_text(
        """{{ catalog.render_assets() }}\n{{ content }}"""
    )

    (folder / "FooBar.css").touch()

    (folder / "common").mkdir()
    (folder / "common" / "Form.jinja").write_text(
        """
{#js "shared.js" #}
<form></form>"""
    )

    (folder / "common" / "Form.css").touch()
    (folder / "common" / "Form.js").touch()

    (folder / "Page.jinja").write_text(
        """
{#css "Page.css" #}
<Layout><common.Form></common.Form></Layout>"""
    )

    (folder / "Page.css").touch()
    (folder / "Page.js").touch()

    html = catalog.render("Page")
    print(html)

    expected  = """
<link rel="stylesheet" href="/static/components/Page.css">
<link rel="stylesheet" href="/static/components/Form.css">
<script type="module" src="/static/components/Page.js"></script>
<script type="module" src="/static/components/shared.js"></script>
<script type="module" src="/static/components/Form.js"></script>
<form></form>
""".strip()

    assert html == Markup(expected)
