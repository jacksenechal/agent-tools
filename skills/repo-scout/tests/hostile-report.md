<!-- Fixture for test_render_html.sh. Every payload below tries to overwrite document.title with PWNED; none may run. -->

# Report </title><script>document.title='PWNED-title'</script>

Normal **bold** text and `code`.

</script><script>document.title='PWNED-script'</script>

<img src=x onerror="document.title='PWNED-img'">

```mermaid
graph TD
  A["start <img src=x onerror=document.title='PWNED-mermaid'>"] --> B[end]
```
