# asitop-exporter
    参考 nvitop-exporter，基于 asitop 开发的 Mac 系统上metrics监控工具
## 一、编译
    pip install prometheus_client Cython pyinstaller requests
### whl
    python setup.py bdist_wheel
### 可执行文件
    cd asitop_exporter
    pyinstaller __main__.spec
## 二、使用
    sudo asitop-exporter -B 10.20.30.40 -p 9999 --interval 60.0 --post_url http://xxx.xxx.xxx.xxx/
    1、程序需要以 sudo 权限运行
    2、程序运行 10.20.30.40 的 9999 端口, 可以通过http请求 http://10.20.30.40:9999/metrics 获取 prometheus 格式的信息
    3、--interval 60.0 监控间隔，表示每60s获取一次信息，默认是5s
    4、--post_url http://xxx.xxx.xxx.xxx/ 监控信息回调接口，以json格式返回。不设置则不会post.
