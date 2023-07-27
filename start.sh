# 以下配置根据自己项目不同，进行响应修改
source tutorial-env/bin/activate

programeName="run.py"

echo "开始重启  ${programeName}"

pid=$(ps -ef | grep ${programeName} | grep -v grep | awk '{print $2}')


echo "查询服务进程id 为 ${pid}"

if [ -n ${pid} ]; then
   # 杀死进程
   kill -9 ${pid}
else
   echo "${progrmeName}进程为空，无法杀死"
fi
# 重启服务
nohup python3 -u ${programeName} &
echo "服务 ${programeName} 已启动"
tail -f nohup.out