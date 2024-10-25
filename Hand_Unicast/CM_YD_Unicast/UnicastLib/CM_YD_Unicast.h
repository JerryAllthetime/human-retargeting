#pragma once
#include <winsock2.h>
#include <atomic>
#include <thread>
#include <mutex>
#include <vector>
#include <memory>
#include "nlohmann/json.hpp"


#pragma comment(lib, "ws2_32.lib")

#ifndef __CM_YD_Glove_H__
#define __CM_YD_Glove_H__

#define YDGlove_SDK __declspec( dllexport )

#endif

using json = nlohmann::json;
using namespace std;

class GloveSDK;

static mutex data_mutex;
static condition_variable data_cond;
static atomic<bool> data_available(false);
static mutex control_console_mux;



/*
* ��������
* Bone data 
*/
struct Bone
{
	string name;
	int parent = 0;
	vector<float> location = {};
	vector<float> rotation = {};
	vector<float> scale = {};	
};

struct Parameter 
{
	string name;
	float value;
};

/*
* ����˫��ָ�ؽ���ת����
* Saving data for both hands finger joint
*/
struct handsfingerJoint
{
	vector<Parameter> fingerJoint_L;
	vector<Parameter> fingerJoint_R;
};

/*
* �˽ṹ�������׵�����
* The glove data is stored within this structure.
*/
struct HandData
{
	Bone bones;
	handsfingerJoint fingerJoints;
};

/*
* �˽ṹ���Ż�ȡ��������
* Get all data is stored within this structure.
*/
struct GloveData
{
	string deviceName;
	HandData handDatas;
};


void print_control_thread(GloveSDK* glove_sdk);

/*
* �ص���������
* Callback function type
*/
using GloveCallBack = function<void(GloveSDK*)>;

/*
* ֻ��ӡ���
*/
void OnlyPrintFrame();

class YDGlove_SDK GloveSDK
{
public:
	/*
	* ��ʼ�� socket ���߳�
	* Init Soicket and thread
	*/
	bool Initialize(const char* udp_ip, unsigned short udp_port);

	/*
	* �ر��̣߳�����socket
	* close thread, clear socket
	*/
	void Shutdown();

	/*
	* �������ݣ�����ȡ����������ͼ������׵�����
	* The amount of glove data depends on the number of glove pairs sent by the software.
	*/
	vector<GloveData>gloveDataList;

	/*
	* ע��ص�����
	* Registering callback function
	*/
	void RegisterGloveCallBack(GloveCallBack callback);

	//Print all data
	void PrintAllGloveData(GloveData inputGloveData);
	

private:
	static const int BUFFER_SIZE = 80000; //�����С //Cache size
	SOCKET m_udp_socket;
	atomic<bool> m_running;
	unique_ptr<thread> m_receive_thread;
	GloveCallBack dataUpdateCallback;

	void ReceiveThread();

	void ParseJson(char* json_buffer, int length);

	void IniData();

};



